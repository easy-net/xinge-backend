import logging
import re
from datetime import datetime

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.models.message import Message
from app.integrations.wechat_pay import TransferResult
from app.repositories.distributor_repository import DistributorRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository


class DistributorService:
    def __init__(self, db, wechat_pay_client=None, settings=None):
        self.db = db
        self.wechat_pay_client = wechat_pay_client
        self.settings = settings
        self.repository = DistributorRepository(db)
        self.report_repository = ReportRepository(db)
        self.user_repository = UserRepository(db)

    def me(self, *, user):
        profile = self._require_distributor(user)
        direct_city_count = self.repository.count_direct_downlines(parent_distributor_id=user.id, distributor_level="city")
        direct_campus_count = self.repository.count_direct_downlines(parent_distributor_id=user.id, distributor_level="campus")
        return {
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() + "Z",
            "distributor_level": profile.distributor_level,
            "downline_total": direct_city_count + direct_campus_count,
            "nickname": user.nickname,
            "parent_distributor_id": profile.parent_distributor_id,
            "quota_remaining": max(profile.quota_total - profile.quota_used, 0),
            "quota_total": profile.quota_total,
            "quota_used": profile.quota_used,
            "report_stats": self.report_repository.stats_for_user(user.id),
            "team_stats": {
                "campus_count": direct_campus_count,
                "city_count": direct_city_count,
                "user_count": direct_city_count + direct_campus_count,
            },
            "total_commission": profile.total_commission,
            "total_sales_amount": profile.total_sales_amount,
            "total_withdrawn_amount": profile.total_withdrawn_amount,
            "unsettled_commission": profile.unsettled_commission,
            "user_id": user.id,
            "withdrawable_amount": max(profile.unsettled_commission, 0),
        }

    def apply(self, *, user, payload: dict):
        if user.is_distributor:
            raise ConflictError(message="already distributor")
        latest_application = self.repository.get_latest_application_for_user(user_id=user.id)
        if latest_application is not None and latest_application.status == "pending":
            raise ConflictError(message="application is pending")
        application = self.repository.create_application(
            user_id=user.id,
            application_id=self._build_application_id(user.id),
            real_name=payload["real_name"],
            phone=payload["phone"],
            reason=payload["reason"],
            target_level=payload["target_level"],
        )
        self.db.commit()
        return {
            "application_id": application.application_id,
            "created_at": application.created_at.isoformat() + "Z",
            "status": application.status,
        }

    def application_status(self, *, user):
        application = self.repository.get_latest_application_for_user(user_id=user.id)
        if application is None:
            raise NotFoundError(message="application not found")
        return {
            "application_id": application.application_id,
            "created_at": application.created_at.isoformat() + "Z",
            "reject_reason": application.reject_reason or None,
            "status": application.status,
            "target_level": application.target_level,
            "updated_at": application.updated_at.isoformat() + "Z",
        }

    def create_withdrawal(self, *, user, amount: int):
        profile = self._require_distributor(user)
        if amount <= 0:
            raise ValidationError(message="amount must be greater than 0")

        withdrawable_amount = max(profile.unsettled_commission, 0)
        if amount > withdrawable_amount:
            raise ValidationError(message="withdraw amount exceeds available balance")

        receiver_name = (user.nickname or user.phone_masked or "微信用户{}".format(user.id)).strip()
        receiver_masked = self._mask_wechat_account(user)
        auto_approve_threshold = getattr(self.settings, "distributor_withdraw_auto_approve_fen", 10000) if self.settings else 10000
        is_auto_transfer = amount < auto_approve_threshold
        logging.getLogger(__name__).info(
            "distributor.withdraw.create_start user_id=%s openid=%s amount=%s withdrawable_before=%s auto_transfer=%s threshold=%s",
            user.id,
            user.openid,
            amount,
            profile.unsettled_commission,
            is_auto_transfer,
            auto_approve_threshold,
        )
        
        # 先扣除余额，确保并发安全
        profile.unsettled_commission = max(profile.unsettled_commission - amount, 0)
        
        withdraw = self.repository.create_withdrawal(
            user_id=user.id,
            withdraw_id=self._build_withdraw_id(user.id),
            amount=amount,
            account_name=receiver_name,
            bank_name="微信零钱",
            bank_account_masked=receiver_masked,
            status="processing" if is_auto_transfer else "pending_review",
        )
        self._record_withdrawal_event(
            withdraw_id=withdraw.withdraw_id,
            event_type="created",
            status=withdraw.status,
            detail="amount={} auto_transfer={}".format(withdraw.amount, is_auto_transfer),
            operator="user:{}".format(user.id),
        )

        transfer_result = None
        if is_auto_transfer:
            try:
                transfer_result = self._process_withdraw_transfer(withdrawal=withdraw, user=user, profile=profile)
            except Exception as error:
                logging.getLogger(__name__).exception(
                    "distributor.withdraw.auto_transfer_failed withdraw_id=%s user_id=%s amount=%s",
                    withdraw.withdraw_id,
                    user.id,
                    amount,
                )
                # 自动转账失败，改为待审核状态，由人工处理
                self.repository.update_withdrawal_status(
                    withdrawal=withdraw,
                    status="pending_review",
                    fail_reason=str(error),
                )
                self._record_withdrawal_event(
                    withdraw_id=withdraw.withdraw_id,
                    event_type="auto_transfer_failed",
                    status=withdraw.status,
                    detail=str(error),
                    operator="system",
                )
                transfer_result = None
        
        self.db.commit()
        logging.getLogger(__name__).info(
            "distributor.withdraw.create_done withdraw_id=%s user_id=%s status=%s amount=%s withdrawable_after=%s transfer_bill_no=%s",
            withdraw.withdraw_id,
            user.id,
            withdraw.status,
            withdraw.amount,
            profile.unsettled_commission,
            getattr(transfer_result, "transfer_bill_no", ""),
        )
        return {
            "withdraw_id": withdraw.withdraw_id,
            "amount": withdraw.amount,
            "status": withdraw.status,
            "channel_name": "微信零钱",
            "receiver_name": receiver_name,
            "receiver_masked": receiver_masked,
            "created_at": withdraw.created_at.isoformat() + "Z",
            "withdrawable_amount_after": profile.unsettled_commission,
            "transfer_bill_no": getattr(transfer_result, "transfer_bill_no", ""),
        }

    def list_withdrawals(self, *, user, page: int, page_size: int):
        self._require_distributor(user)
        items, total = self.repository.list_withdrawals_for_user(user_id=user.id, page=page, page_size=page_size)
        return {
            "list": [
                {
                    "amount": item.amount,
                    "bank_account_masked": item.bank_account_masked,
                    "bank_name": item.bank_name,
                    "channel_name": item.bank_name or "微信零钱",
                    "receiver_name": item.account_name,
                    "receiver_masked": item.bank_account_masked,
                    "completed_at": item.completed_at.isoformat() + "Z" if item.completed_at else None,
                    "created_at": item.created_at.isoformat() + "Z",
                    "fail_reason": item.fail_reason or "",
                    "status": item.status,
                    "transfer_bill_no": item.transfer_bill_no or "",
                    "withdraw_id": item.withdraw_id,
                }
                for item in items
            ],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def list_downlines(self, *, user, page: int, page_size: int, level=None):
        self._require_distributor(user)
        items, total = self.repository.list_direct_downlines(
            parent_distributor_id=user.id,
            page=page,
            page_size=page_size,
            distributor_level=level,
        )
        return {
            "list": [
                {
                    "avatar_url": downline_user.avatar_url,
                    "distributor_level": downline_profile.distributor_level,
                    "joined_at": downline_profile.created_at.isoformat() + "Z",
                    "nickname": downline_user.nickname or downline_user.phone_masked or "用户{}".format(downline_user.id),
                    "phone_masked": downline_user.phone_masked or None,
                    "quota_remaining": max(downline_profile.quota_total - downline_profile.quota_used, 0),
                    "quota_total": downline_profile.quota_total,
                    "quota_used": downline_profile.quota_used,
                    "report_stats": self.report_repository.stats_for_user(downline_user.id),
                    "user_id": downline_user.id,
                }
                for downline_profile, downline_user in items
            ],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def allocate_quota(self, *, user, downline_user_id: int, amount: int):
        profile = self._require_distributor(user)
        if profile.distributor_level == "campus":
            raise ForbiddenError(message="campus distributor cannot allocate quota")
        if amount <= 0:
            raise ValidationError(message="amount must be greater than 0")

        downline_user = self.user_repository.get_by_id(downline_user_id)
        if downline_user is None:
            raise NotFoundError(message="downline not found")
        downline_profile = self.repository.get_profile_for_user(user_id=downline_user_id)
        if downline_profile is None:
            if user.role == "admin":
                downline_user.role = "distributor"
                downline_user.is_distributor = True
                downline_profile = self.repository.create_profile(
                    user_id=downline_user_id,
                    distributor_level="campus",
                    parent_distributor_id=user.id,
                    quota_total=0,
                )
            else:
                raise NotFoundError(message="downline not found")
        if user.role != "admin" and downline_profile.parent_distributor_id != user.id:
            raise ForbiddenError(message="downline is not directly managed by current distributor")
        if user.role == "admin" and downline_profile.parent_distributor_id is None and downline_user_id != user.id:
            downline_profile.parent_distributor_id = user.id

        my_remaining_before = max(profile.quota_total - profile.quota_used, 0)
        if amount > my_remaining_before:
            raise ValidationError(message="quota is insufficient")

        my_remaining_after = my_remaining_before - amount
        downline_remaining_before = max(downline_profile.quota_total - downline_profile.quota_used, 0)
        downline_remaining_after = downline_remaining_before + amount

        profile.quota_used += amount
        downline_profile.quota_total += amount

        self.repository.create_quota_record(
            user_id=user.id,
            direction="out",
            counterparty_user_id=downline_user_id,
            counterparty_level=downline_profile.distributor_level,
            amount=amount,
            quota_before=my_remaining_before,
            quota_after=my_remaining_after,
            remark="分配给下级分销",
        )
        self.repository.create_quota_record(
            user_id=downline_user_id,
            direction="in",
            counterparty_user_id=user.id,
            counterparty_level=profile.distributor_level,
            amount=amount,
            quota_before=downline_remaining_before,
            quota_after=downline_remaining_after,
            remark="上级分配给我",
        )
        self.db.commit()
        return {
            "allocated_amount": amount,
            "downline_quota": {
                "nickname": getattr(downline_profile.user, "nickname", ""),
                "quota_remaining": downline_remaining_after,
                "quota_total": downline_profile.quota_total,
                "user_id": downline_user_id,
            },
            "my_quota": {
                "quota_allocated": profile.quota_used,
                "quota_remaining": my_remaining_after,
                "quota_total": profile.quota_total,
            },
        }

    def list_quota_records(self, *, user, page: int, page_size: int):
        self._require_distributor(user)
        items, total = self.repository.list_quota_records_for_user(user_id=user.id, page=page, page_size=page_size)
        return {
            "list": [
                {
                    "record_id": record.id,
                    "direction": record.direction,
                    "counterparty_user_id": record.counterparty_user_id,
                    "counterparty_name": counterparty.nickname if counterparty else "",
                    "counterparty_level": record.counterparty_level,
                    "quantity": record.amount,
                    "quota_before": record.quota_before,
                    "quota_after": record.quota_after,
                    "created_at": record.created_at.isoformat() + "Z",
                    "remark": record.remark,
                }
                for record, counterparty in items
            ],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def admin_list_applications(self, *, page: int, page_size: int, status=None):
        items, total = self.repository.list_applications(page=page, page_size=page_size, status=status)
        return {
            "list": [
                {
                    "application_id": item.application_id,
                    "user_id": item.user_id,
                    "real_name": item.real_name,
                    "phone": item.phone,
                    "reason": item.reason,
                    "status": item.status,
                    "target_level": item.target_level,
                    "reject_reason": item.reject_reason or None,
                    "created_at": item.created_at.isoformat() + "Z",
                    "updated_at": item.updated_at.isoformat() + "Z",
                }
                for item in items
            ],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def admin_approve_application(self, *, application_id: str):
        application = self._require_pending_application(application_id)
        profile = self.repository.get_profile_for_user(user_id=application.user_id)
        if profile is None:
            self.repository.create_profile(
                user_id=application.user_id,
                distributor_level=application.target_level,
                quota_total=self._default_quota_for_level(application.target_level),
            )
        user = application.user
        user.is_distributor = True
        self.repository.update_application_status(application=application, status="approved")
        self.db.add(
            Message(
                user_id=user.id,
                type="distributor_approved",
                title="分销申请已通过",
                content="您的分销申请已通过审核，当前级别为 {}。".format(application.target_level),
                is_read=False,
            )
        )
        self.db.commit()
        return {
            "application_id": application.application_id,
            "status": application.status,
            "user_id": user.id,
            "distributor_level": application.target_level,
        }

    def admin_reject_application(self, *, application_id: str, reject_reason: str):
        application = self._require_pending_application(application_id)
        user = application.user
        reason = reject_reason.strip() or "申请资料暂不满足要求"
        self.repository.update_application_status(application=application, status="rejected", reject_reason=reason)
        self.db.add(
            Message(
                user_id=user.id,
                type="distributor_rejected",
                title="分销申请未通过",
                content="您的分销申请未通过审核：{}".format(reason),
                is_read=False,
            )
        )
        self.db.commit()
        return {
            "application_id": application.application_id,
            "reject_reason": application.reject_reason,
            "status": application.status,
            "user_id": user.id,
        }

    def admin_list_withdrawals(self, *, page: int, page_size: int, status=None):
        items, total = self.repository.list_withdrawals(page=page, page_size=page_size, status=status)
        return {
            "list": [
                {
                    "withdraw_id": withdrawal.withdraw_id,
                    "user_id": withdrawal.user_id,
                    "nickname": user.nickname or "用户{}".format(user.id),
                    "avatar_url": user.avatar_url,
                    "amount": withdrawal.amount,
                    "status": withdrawal.status,
                    "channel_name": withdrawal.bank_name or "微信零钱",
                    "receiver_name": withdrawal.account_name,
                    "receiver_masked": withdrawal.bank_account_masked,
                    "created_at": withdrawal.created_at.isoformat() + "Z",
                    "completed_at": withdrawal.completed_at.isoformat() + "Z" if withdrawal.completed_at else None,
                    "fail_reason": withdrawal.fail_reason or "",
                    "transfer_bill_no": withdrawal.transfer_bill_no or "",
                }
                for withdrawal, user in items
            ],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def admin_approve_withdrawal(self, *, withdraw_id: str):
        withdrawal = self._require_reviewable_withdrawal(withdraw_id)
        user = withdrawal.user
        profile = self._require_distributor(user)
        logging.getLogger(__name__).info(
            "distributor.withdraw.admin_approve_start withdraw_id=%s user_id=%s amount=%s current_status=%s balance_before=%s",
            withdrawal.withdraw_id,
            user.id,
            withdrawal.amount,
            withdrawal.status,
            profile.unsettled_commission,
        )
        if self._should_bypass_admin_withdraw_approval():
            transfer_result = self._approve_withdrawal_without_validation(withdrawal=withdrawal, profile=profile)
            self.db.commit()
            logging.getLogger(__name__).info(
                "distributor.withdraw.admin_approve_bypassed withdraw_id=%s status=%s transfer_state=%s transfer_bill_no=%s",
                withdrawal.withdraw_id,
                withdrawal.status,
                transfer_result.state,
                transfer_result.transfer_bill_no,
            )
            return {
                "withdraw_id": withdrawal.withdraw_id,
                "status": withdrawal.status,
                "amount": withdrawal.amount,
                "transfer_state": transfer_result.state,
                "transfer_bill_no": transfer_result.transfer_bill_no,
                "package_info": transfer_result.package_info,
                "completed_at": withdrawal.completed_at.isoformat() + "Z" if withdrawal.completed_at else None,
            }
        try:
            transfer_result = self._process_withdraw_transfer(withdrawal=withdrawal, user=user, profile=profile)
        except Exception as error:
            profile.unsettled_commission += withdrawal.amount
            self.repository.update_withdrawal_status(
                withdrawal=withdrawal,
                status="failed",
                completed_at=datetime.utcnow(),
                fail_reason=str(error),
            )
            self._record_withdrawal_event(
                withdraw_id=withdrawal.withdraw_id,
                event_type="admin_approve_failed",
                status=withdrawal.status,
                detail=str(error),
                operator="admin",
            )
            self.db.commit()
            logging.getLogger(__name__).exception(
                "distributor.withdraw.admin_approve_failed withdraw_id=%s user_id=%s amount=%s restored_balance=%s",
                withdrawal.withdraw_id,
                user.id,
                withdrawal.amount,
                profile.unsettled_commission,
            )
            raise
        self.db.commit()
        logging.getLogger(__name__).info(
            "distributor.withdraw.admin_approve_done withdraw_id=%s status=%s transfer_state=%s transfer_bill_no=%s completed_at=%s",
            withdrawal.withdraw_id,
            withdrawal.status,
            transfer_result.state,
            transfer_result.transfer_bill_no,
            withdrawal.completed_at.isoformat() + "Z" if withdrawal.completed_at else None,
        )
        return {
            "withdraw_id": withdrawal.withdraw_id,
            "status": withdrawal.status,
            "amount": withdrawal.amount,
            "transfer_state": transfer_result.state,
            "transfer_bill_no": transfer_result.transfer_bill_no,
            "package_info": transfer_result.package_info,
            "completed_at": withdrawal.completed_at.isoformat() + "Z" if withdrawal.completed_at else None,
        }

    def admin_reject_withdrawal(self, *, withdraw_id: str):
        withdrawal = self._require_reviewable_withdrawal(withdraw_id)
        profile = self.repository.get_profile_for_user(user_id=withdrawal.user_id)
        if profile is not None:
            profile.unsettled_commission += withdrawal.amount
        self.repository.update_withdrawal_status(withdrawal=withdrawal, status="rejected", completed_at=datetime.utcnow())
        self._record_withdrawal_event(
            withdraw_id=withdrawal.withdraw_id,
            event_type="admin_rejected",
            status=withdrawal.status,
            detail="amount_returned={}".format(withdrawal.amount),
            operator="admin",
        )
        self.db.commit()
        logging.getLogger(__name__).info(
            "distributor.withdraw.admin_reject withdraw_id=%s user_id=%s amount=%s restored_balance=%s",
            withdrawal.withdraw_id,
            withdrawal.user_id,
            withdrawal.amount,
            getattr(profile, "unsettled_commission", None),
        )
        return {
            "withdraw_id": withdrawal.withdraw_id,
            "status": withdrawal.status,
            "amount": withdrawal.amount,
        }

    def admin_get_withdrawal_debug(self, *, withdraw_id: str):
        withdrawal = self.repository.get_withdrawal_by_withdraw_id(withdraw_id=withdraw_id)
        if withdrawal is None:
            raise NotFoundError(message="withdrawal not found")

        user = withdrawal.user
        profile = self.repository.get_profile_for_user(user_id=withdrawal.user_id)
        callback_url = ""
        if self.settings:
            callback_url = getattr(self.settings, "wechat_transfer_notify_url", "") or getattr(self.settings, "wechat_notify_url", "")

        expected_out_bill_no = self._build_wechat_transfer_bill_no(withdrawal.withdraw_id)
        timeline = self.repository.list_withdrawal_events(withdraw_id=withdrawal.withdraw_id)
        return {
            "withdraw_id": withdrawal.withdraw_id,
            "user_id": withdrawal.user_id,
            "nickname": getattr(user, "nickname", "") or "用户{}".format(withdrawal.user_id),
            "openid": getattr(user, "openid", ""),
            "status": withdrawal.status,
            "amount": withdrawal.amount,
            "amount_yuan": "{:.2f}".format(withdrawal.amount / 100.0),
            "receiver_name": withdrawal.account_name,
            "receiver_masked": withdrawal.bank_account_masked,
            "channel_name": withdrawal.bank_name or "微信零钱",
            "created_at": withdrawal.created_at.isoformat() + "Z",
            "completed_at": withdrawal.completed_at.isoformat() + "Z" if withdrawal.completed_at else None,
            "transfer_bill_no": withdrawal.transfer_bill_no or "",
            "fail_reason": withdrawal.fail_reason or "",
            "withdrawable_balance_now": getattr(profile, "unsettled_commission", 0),
            "total_withdrawn_amount": getattr(profile, "total_withdrawn_amount", 0),
            "expected_out_bill_no": expected_out_bill_no,
            "expected_callback_url": callback_url,
            "diagnostics": {
                "has_openid": bool(getattr(user, "openid", "")),
                "has_transfer_bill_no": bool(withdrawal.transfer_bill_no),
                "waiting_callback": withdrawal.status == "processing",
                "is_terminal_status": withdrawal.status in {"paid", "rejected", "failed"},
                "is_manual_review_status": withdrawal.status == "pending_review",
                "wechat_pay_client_configured": bool(self.wechat_pay_client),
                "callback_url_configured": bool(callback_url),
            },
            "timeline": [
                {
                    "event_type": item.event_type,
                    "status": item.status,
                    "detail": item.detail,
                    "operator": item.operator,
                    "created_at": item.created_at.isoformat() + "Z",
                }
                for item in timeline
            ],
        }

    def admin_debug_transfer_callback(self, *, withdraw_id: str, state: str, fail_reason: str = ""):
        withdrawal = self.repository.get_withdrawal_by_withdraw_id(withdraw_id=withdraw_id)
        if withdrawal is None:
            raise NotFoundError(message="withdrawal not found")
        simulated_transfer_bill_no = withdrawal.transfer_bill_no or "debug-transfer-{}".format(self._build_wechat_transfer_bill_no(withdraw_id))
        result = self.handle_transfer_callback(
            transfer_bill_no=simulated_transfer_bill_no,
            state=state,
            out_bill_no=self._build_wechat_transfer_bill_no(withdraw_id),
            fail_reason=fail_reason,
        )
        logging.getLogger(__name__).info(
            "distributor.withdraw.debug_callback withdraw_id=%s simulated_state=%s transfer_bill_no=%s result_status=%s",
            withdraw_id,
            state,
            simulated_transfer_bill_no,
            result.get("status"),
        )
        return result

    def admin_seed_quota_records(self, *, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="user not found")

        user.role = "distributor"
        user.is_distributor = True
        profile = self.repository.get_profile_for_user(user_id=user.id)
        if profile is None:
            profile = self.repository.create_profile(
                user_id=user.id,
                distributor_level="city",
                quota_total=500,
            )
        elif profile.quota_total < 500:
            profile.quota_total = 500

        parent_user = self.user_repository.get_by_openid("seed-parent-{}".format(user.id))
        if parent_user is None:
            parent_user = self.user_repository.create_user(
                openid="seed-parent-{}".format(user.id),
                unionid="seed-parent-union-{}".format(user.id),
            )
        parent_user.nickname = parent_user.nickname or "测试上级分销"
        parent_user.role = "distributor"
        parent_user.is_distributor = True
        parent_profile = self.repository.get_profile_for_user(user_id=parent_user.id)
        if parent_profile is None:
            parent_profile = self.repository.create_profile(
                user_id=parent_user.id,
                distributor_level="strategic",
                quota_total=1000,
            )

        child_user = self.user_repository.get_by_openid("seed-child-{}".format(user.id))
        if child_user is None:
            child_user = self.user_repository.create_user(
                openid="seed-child-{}".format(user.id),
                unionid="seed-child-union-{}".format(user.id),
            )
        child_user.nickname = child_user.nickname or "测试城市分销"
        child_user.role = "distributor"
        child_user.is_distributor = True
        child_profile = self.repository.get_profile_for_user(user_id=child_user.id)
        if child_profile is None:
            child_profile = self.repository.create_profile(
                user_id=child_user.id,
                distributor_level="campus",
                parent_distributor_id=user.id,
                quota_total=120,
            )
        else:
            child_profile.parent_distributor_id = user.id

        profile.parent_distributor_id = parent_user.id

        # 上级分配给我
        self.repository.create_quota_record(
            user_id=user.id,
            direction="in",
            counterparty_user_id=parent_user.id,
            counterparty_level=parent_profile.distributor_level,
            amount=300,
            quota_before=200,
            quota_after=500,
            remark="上级分配给我",
        )
        # 我分配给下级
        self.repository.create_quota_record(
            user_id=user.id,
            direction="out",
            counterparty_user_id=child_user.id,
            counterparty_level=child_profile.distributor_level,
            amount=100,
            quota_before=500,
            quota_after=400,
            remark="分配给城市分销",
        )
        self.repository.create_quota_record(
            user_id=user.id,
            direction="out",
            counterparty_user_id=child_user.id,
            counterparty_level=child_profile.distributor_level,
            amount=50,
            quota_before=400,
            quota_after=350,
            remark="分配给城市分销",
        )
        # 下级视角也补一条收入记录，方便切账号时查看
        self.repository.create_quota_record(
            user_id=child_user.id,
            direction="in",
            counterparty_user_id=user.id,
            counterparty_level=profile.distributor_level,
            amount=100,
            quota_before=20,
            quota_after=120,
            remark="上级分配给我",
        )

        self.db.commit()
        return {
            "user_id": user.id,
            "seeded": 4,
            "parent_user_id": parent_user.id,
            "child_user_id": child_user.id,
            "distributor_level": profile.distributor_level,
        }

    def admin_list_distributors(self, *, page: int, page_size: int, level=None):
        items, total = self.repository.list_profiles(page=page, page_size=page_size, distributor_level=level)
        return {
            "list": [
                {
                    "user_id": profile.user_id,
                    "nickname": distributor_user.nickname,
                    "avatar_url": distributor_user.avatar_url,
                    "distributor_level": profile.distributor_level,
                    "parent_distributor_id": profile.parent_distributor_id,
                    "quota_total": profile.quota_total,
                    "quota_used": profile.quota_used,
                    "quota_remaining": max(profile.quota_total - profile.quota_used, 0),
                    "unsettled_commission": profile.unsettled_commission,
                    "withdrawable_amount": max(profile.unsettled_commission, 0),
                    "created_at": profile.created_at.isoformat() + "Z",
                }
                for profile, distributor_user in items
            ],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def admin_list_assignable_users(self, *, page: int, page_size: int, keyword: str = ""):
        items, total = self.user_repository.list_users_with_total(page=page, page_size=page_size, keyword=keyword)
        list_items = []
        for item in items:
            profile = self.repository.get_profile_for_user(user_id=item.id)
            list_items.append(
                {
                    "user_id": item.id,
                    "nickname": item.nickname or item.phone_masked or "用户{}".format(item.id),
                    "avatar_url": item.avatar_url,
                    "openid": item.openid,
                    "phone_masked": item.phone_masked or None,
                    "role": item.role,
                    "is_distributor": item.is_distributor,
                    "distributor_level": getattr(profile, "distributor_level", None),
                    "parent_distributor_id": getattr(profile, "parent_distributor_id", None),
                    "created_at": item.created_at.isoformat() + "Z",
                }
            )
        return {
            "list": list_items,
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def admin_list_distributor_downlines(self, *, user_id: int, page: int, page_size: int, level=None):
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="user not found")
        if user.role == "admin":
            users = self.user_repository.list_users(page=page, page_size=page_size, exclude_user_id=user.id)
            list_items = []
            for item in users:
                profile = self.repository.get_profile_for_user(user_id=item.id)
                profile_level = getattr(profile, "distributor_level", "campus")
                if level and profile_level != level:
                    continue
                quota_total = getattr(profile, "quota_total", 0)
                quota_used = getattr(profile, "quota_used", 0)
                joined_at = getattr(profile, "created_at", item.created_at)
                list_items.append(
                    {
                        "avatar_url": item.avatar_url,
                        "distributor_level": profile_level,
                        "joined_at": joined_at.isoformat() + "Z",
                        "nickname": item.nickname,
                        "quota_remaining": max(quota_total - quota_used, 0),
                        "quota_total": quota_total,
                        "quota_used": quota_used,
                        "report_stats": self.report_repository.stats_for_user(item.id),
                        "user_id": item.id,
                    }
                )
            return {
                "list": list_items,
                "page": page,
                "page_size": page_size,
                "page_total": 1 if list_items else 0,
                "total": len(list_items),
                "source_user_id": user_id,
            }
        data = self.list_downlines(user=user, page=page, page_size=page_size, level=level)
        data["source_user_id"] = user_id
        return data

    def admin_allocate_quota(self, *, user_id: int, downline_user_id: int, amount: int):
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="user not found")
        data = self.allocate_quota(user=user, downline_user_id=downline_user_id, amount=amount)
        data["source_user_id"] = user_id
        return data

    def admin_assign_downline(self, *, user_id: int, downline_user_id: int, distributor_level: str = ""):
        parent_user = self.user_repository.get_by_id(user_id)
        if parent_user is None:
            raise NotFoundError(message="parent user not found")

        parent_profile = self.repository.get_profile_for_user(user_id=parent_user.id)
        if parent_user.role != "admin" and parent_profile is None:
            raise ValidationError(message="parent user is not a distributor")
        if parent_profile is not None and parent_profile.distributor_level == "campus":
            raise ForbiddenError(message="campus distributor cannot manage downlines")

        child_user = self.user_repository.get_by_id(downline_user_id)
        if child_user is None:
            raise NotFoundError(message="downline user not found")
        if child_user.id == parent_user.id:
            raise ValidationError(message="cannot assign self as downline")
        if child_user.role == "admin":
            raise ValidationError(message="admin user cannot be assigned as downline")

        child_profile = self.repository.get_profile_for_user(user_id=child_user.id)
        parent_level = "admin" if parent_user.role == "admin" and parent_profile is None else parent_profile.distributor_level
        target_level = (distributor_level or getattr(child_profile, "distributor_level", "") or self._default_downline_level(parent_level)).strip().lower()
        self._validate_downline_level(parent_level=parent_level, child_level=target_level)

        if self._would_create_downline_cycle(parent_user_id=parent_user.id, downline_user_id=child_user.id):
            raise ValidationError(message="cannot assign ancestor as direct downline")

        previous_parent_id = getattr(child_profile, "parent_distributor_id", None)
        if child_profile is None:
            child_profile = self.repository.create_profile(
                user_id=child_user.id,
                distributor_level=target_level,
                parent_distributor_id=parent_user.id,
                quota_total=0,
            )
        else:
            child_profile.distributor_level = target_level
            child_profile.parent_distributor_id = parent_user.id

        child_user.role = "distributor"
        child_user.is_distributor = True
        self.db.commit()
        return {
            "user_id": parent_user.id,
            "downline_user_id": child_user.id,
            "previous_parent_distributor_id": previous_parent_id,
            "parent_distributor_id": child_profile.parent_distributor_id,
            "distributor_level": child_profile.distributor_level,
            "status": "assigned",
        }

    def admin_unassign_downline(self, *, user_id: int, downline_user_id: int):
        parent_user = self.user_repository.get_by_id(user_id)
        if parent_user is None:
            raise NotFoundError(message="parent user not found")

        child_user = self.user_repository.get_by_id(downline_user_id)
        if child_user is None:
            raise NotFoundError(message="downline user not found")

        child_profile = self.repository.get_profile_for_user(user_id=child_user.id)
        if child_profile is None:
            raise NotFoundError(message="downline profile not found")
        if child_profile.parent_distributor_id != parent_user.id:
            raise ValidationError(message="downline is not directly assigned to current parent")

        direct_downlines = self.repository.count_direct_downlines(parent_distributor_id=child_user.id)
        if direct_downlines > 0:
            raise ValidationError(message="cannot unassign distributor with existing downlines")

        previous_parent_id = child_profile.parent_distributor_id
        child_profile.parent_distributor_id = None
        self.db.commit()
        return {
            "user_id": parent_user.id,
            "downline_user_id": child_user.id,
            "previous_parent_distributor_id": previous_parent_id,
            "parent_distributor_id": None,
            "distributor_level": child_profile.distributor_level,
            "status": "unassigned",
        }

    def admin_update_distributor(self, *, user_id: int, distributor_level: str = "", unsettled_commission: int = 0):
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="user not found")
        profile = self.repository.get_profile_for_user(user_id=user.id)
        if profile is None:
            raise NotFoundError(message="distributor profile not found")

        target_level = (distributor_level or profile.distributor_level).strip().lower()
        if target_level not in {"strategic", "city", "campus"}:
            raise ValidationError(message="invalid distributor level")

        if unsettled_commission < 0:
            raise ValidationError(message="withdrawable amount cannot be negative")

        direct_downlines = self.repository.count_direct_downlines(parent_distributor_id=user.id)
        if target_level == "campus" and direct_downlines > 0:
            raise ValidationError(message="campus distributor cannot keep existing downlines")

        parent_profile = self.repository.get_profile_for_user(user_id=profile.parent_distributor_id) if profile.parent_distributor_id else None
        parent_level = getattr(parent_profile, "distributor_level", "admin" if user.role == "admin" else "")
        if parent_profile is not None:
            self._validate_downline_level(parent_level=parent_level, child_level=target_level)

        previous_level = profile.distributor_level
        previous_unsettled_commission = profile.unsettled_commission
        profile.distributor_level = target_level
        profile.unsettled_commission = unsettled_commission
        self.db.commit()
        return {
            "user_id": user.id,
            "distributor_level": profile.distributor_level,
            "previous_distributor_level": previous_level,
            "unsettled_commission": profile.unsettled_commission,
            "withdrawable_amount": max(profile.unsettled_commission, 0),
            "previous_unsettled_commission": previous_unsettled_commission,
            "status": "updated",
        }

    def _require_distributor(self, user):
        logger = logging.getLogger(__name__)
        profile = self.repository.get_profile_for_user(user_id=user.id)
        logger.info(
            "distributor.access.check user_id=%s open_id=%s is_distributor=%s profile_exists=%s distributor_level=%s",
            user.id,
            user.openid,
            user.is_distributor,
            bool(profile),
            getattr(profile, "distributor_level", None),
        )
        if not user.is_distributor or profile is None:
            raise ForbiddenError(message="distributor access required")
        return profile

    def _build_application_id(self, user_id: int) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return "app_{}_{}".format(timestamp, str(user_id).zfill(6))

    def _build_withdraw_id(self, user_id: int) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return "WD{}{}".format(timestamp, str(user_id).zfill(6))

    def _process_withdraw_transfer(self, *, withdrawal, user, profile):
        """处理微信转账，支持同步成功和异步受理两种模式
        
        返回:
            TransferResult: 转账结果
            
        状态处理:
            - SUCCESS: 转账成功，更新为 paid
            - ACCEPTED/PROCESSING: 已受理，更新为 processing，等待异步回调
            - 其他: 视为失败，抛出异常
        """
        if not self.wechat_pay_client:
            raise ValidationError(message="wechat pay client is not configured")
        if not user.openid:
            raise ValidationError(message="user openid is missing")
        out_bill_no = self._build_wechat_transfer_bill_no(withdrawal.withdraw_id)
        transfer_result = self.wechat_pay_client.transfer_to_balance(
            out_bill_no=out_bill_no,
            amount=withdrawal.amount,
            openid=user.openid,
            user_name=withdrawal.account_name,
        )
        transfer_state = (transfer_result.state or "").upper()
        
        if transfer_state == "SUCCESS":
            # 同步成功，直接标记为已到账
            completed_at = datetime.utcnow()
            self.repository.update_withdrawal_status(
                withdrawal=withdrawal,
                status="paid",
                completed_at=completed_at,
                transfer_bill_no=transfer_result.transfer_bill_no,
            )
            profile.total_withdrawn_amount += withdrawal.amount
            self._record_withdrawal_event(
                withdraw_id=withdrawal.withdraw_id,
                event_type="transfer_success",
                status=withdrawal.status,
                detail="transfer_bill_no={}".format(transfer_result.transfer_bill_no),
                operator="wechat",
            )
            logging.getLogger(__name__).info(
                "distributor.withdraw.transfer_success withdraw_id=%s transfer_bill_no=%s amount=%s",
                withdrawal.withdraw_id,
                transfer_result.transfer_bill_no,
                withdrawal.amount,
            )
        elif transfer_state in ("ACCEPTED", "PROCESSING", "WAIT_PAY", "WAIT_USER_CONFIRM"):
            # 已受理，等待异步回调
            self.repository.update_withdrawal_status(
                withdrawal=withdrawal,
                status="processing",
                completed_at=None,
                transfer_bill_no=transfer_result.transfer_bill_no,
            )
            self._record_withdrawal_event(
                withdraw_id=withdrawal.withdraw_id,
                event_type="transfer_accepted",
                status=withdrawal.status,
                detail="state={} transfer_bill_no={}".format(transfer_state, transfer_result.transfer_bill_no),
                operator="wechat",
            )
            logging.getLogger(__name__).info(
                "distributor.withdraw.transfer_accepted withdraw_id=%s transfer_bill_no=%s amount=%s state=%s",
                withdrawal.withdraw_id,
                transfer_result.transfer_bill_no,
                withdrawal.amount,
                transfer_state,
            )
        else:
            # 其他状态视为失败
            raise ValidationError(message=f"transfer failed with state: {transfer_state}")
            
        return transfer_result

    def _build_wechat_transfer_bill_no(self, withdraw_id: str) -> str:
        sanitized = re.sub(r"[^0-9A-Za-z]", "", withdraw_id or "").upper()
        if not sanitized:
            raise ValidationError(message="invalid withdraw id for wechat transfer")
        return sanitized[:32]

    def _should_bypass_admin_withdraw_approval(self) -> bool:
        return bool(self.settings and getattr(self.settings, "unsafe_admin_withdraw_approve", False))

    def _approve_withdrawal_without_validation(self, *, withdrawal, profile) -> TransferResult:
        transfer_bill_no = "mock-admin-{}".format(self._build_wechat_transfer_bill_no(withdrawal.withdraw_id))
        completed_at = datetime.utcnow()
        self.repository.update_withdrawal_status(
            withdrawal=withdrawal,
            status="paid",
            completed_at=completed_at,
            transfer_bill_no=transfer_bill_no,
            fail_reason="",
        )
        profile.total_withdrawn_amount += withdrawal.amount
        self._record_withdrawal_event(
            withdraw_id=withdrawal.withdraw_id,
            event_type="admin_approve_bypassed",
            status=withdrawal.status,
            detail="transfer_bill_no={}".format(transfer_bill_no),
            operator="admin",
        )
        return TransferResult(
            out_bill_no=self._build_wechat_transfer_bill_no(withdrawal.withdraw_id),
            transfer_bill_no=transfer_bill_no,
            state="SUCCESS",
            package_info="unsafe-admin-withdraw-approve",
        )

    def _mask_wechat_account(self, user) -> str:
        if user.phone_masked:
            return user.phone_masked
        if user.openid:
            return "{}***{}".format(user.openid[:3], user.openid[-4:])
        return "wx-user-{}".format(user.id)

    def handle_transfer_callback(self, *, transfer_bill_no: str, state: str, out_bill_no: str = "", fail_reason: str = ""):
        """处理微信支付转账异步回调
        
        Args:
            transfer_bill_no: 微信转账单号
            state: 转账状态 (SUCCESS/FAILED)
            out_bill_no: 商户转账单号（可选，用于关联提现记录）
            
        处理逻辑:
            - SUCCESS: 更新提现状态为 paid，更新累计提现金额
            - FAILED: 将金额退回用户余额，更新状态为 failed
        """
        logger = logging.getLogger(__name__)
        
        withdrawal = None
        withdraw_id = self._extract_withdraw_id_from_bill_no(out_bill_no) if out_bill_no else None
        if withdraw_id:
            withdrawal = self.repository.get_withdrawal_by_withdraw_id(withdraw_id=withdraw_id)
        if withdrawal is None and transfer_bill_no:
            withdrawal = self.repository.get_withdrawal_by_transfer_bill_no(transfer_bill_no=transfer_bill_no)
        if withdrawal is None:
            logger.error(
                "distributor.withdraw.callback.not_found withdraw_id=%s transfer_bill_no=%s",
                withdraw_id,
                transfer_bill_no,
            )
            raise NotFoundError(message="withdrawal not found")
        withdraw_id = withdrawal.withdraw_id
            
        if withdrawal.status not in ("processing", "pending_review"):
            logger.warning("distributor.withdraw.callback.already_processed withdraw_id=%s current_status=%s", 
                          withdraw_id, withdrawal.status)
            return {"withdraw_id": withdraw_id, "status": withdrawal.status, "message": "already processed"}
        
        profile = self.repository.get_profile_for_user(user_id=withdrawal.user_id)
        state_upper = (state or "").upper()
        
        if state_upper == "SUCCESS":
            # 转账成功
            completed_at = datetime.utcnow()
            self.repository.update_withdrawal_status(
                withdrawal=withdrawal,
                status="paid",
                completed_at=completed_at,
                transfer_bill_no=transfer_bill_no,
            )
            if profile:
                profile.total_withdrawn_amount += withdrawal.amount
            self._record_withdrawal_event(
                withdraw_id=withdraw_id,
                event_type="callback_success",
                status="paid",
                detail="transfer_bill_no={}".format(transfer_bill_no),
                operator="wechat-callback",
            )
            logger.info(
                "distributor.withdraw.callback.success withdraw_id=%s transfer_bill_no=%s amount=%s",
                withdraw_id, transfer_bill_no, withdrawal.amount
            )
            self.db.commit()
            return {
                "withdraw_id": withdraw_id,
                "status": "paid",
                "amount": withdrawal.amount,
                "transfer_bill_no": transfer_bill_no,
            }
        else:
            # 转账失败，退回金额
            if profile:
                profile.unsettled_commission += withdrawal.amount
            self.repository.update_withdrawal_status(
                withdrawal=withdrawal,
                status="failed",
                completed_at=datetime.utcnow(),
                transfer_bill_no=transfer_bill_no,
                fail_reason=fail_reason or state,
            )
            self._record_withdrawal_event(
                withdraw_id=withdraw_id,
                event_type="callback_failed",
                status="failed",
                detail=fail_reason or state,
                operator="wechat-callback",
            )
            logger.error(
                "distributor.withdraw.callback.failed withdraw_id=%s transfer_bill_no=%s amount=%s state=%s",
                withdraw_id, transfer_bill_no, withdrawal.amount, state
            )
            self.db.commit()
            return {
                "withdraw_id": withdraw_id,
                "status": "failed",
                "amount": withdrawal.amount,
                "refunded": True,
            }

    def _extract_withdraw_id_from_bill_no(self, out_bill_no: str) -> str:
        """从商户转账单号中提取提现ID
        
        商户单号格式: WD20250426120000100001（由 _build_wechat_transfer_bill_no 生成）
        直接返回原字符串，因为提现ID已经是这种格式
        """
        # 如果 out_bill_no 被截断或转换过，需要还原
        # 目前直接返回，因为 _build_wechat_transfer_bill_no 已经处理了格式
        return out_bill_no if out_bill_no.startswith("WD") else None

    def _require_pending_application(self, application_id: str):
        application = self.repository.get_application_by_application_id(application_id=application_id)
        if application is None:
            raise NotFoundError(message="application not found")
        if application.status != "pending":
            raise ConflictError(message="application is already reviewed")
        return application

    def _require_reviewable_withdrawal(self, withdraw_id: str):
        withdrawal = self.repository.get_withdrawal_by_withdraw_id(withdraw_id=withdraw_id)
        if withdrawal is None:
            raise NotFoundError(message="withdrawal not found")
        if withdrawal.status != "pending_review":
            raise ConflictError(message="withdrawal is already reviewed")
        return withdrawal

    def _default_quota_for_level(self, distributor_level: str) -> int:
        defaults = {
            "strategic": 500,
            "city": 200,
            "campus": 50,
        }
        return defaults.get(distributor_level, 0)

    def _record_withdrawal_event(self, *, withdraw_id: str, event_type: str, status: str = "", detail: str = "", operator: str = ""):
        self.repository.create_withdrawal_event(
            withdraw_id=withdraw_id,
            event_type=event_type,
            status=status,
            detail=(detail or "")[:1024],
            operator=(operator or "")[:64],
        )

    def _default_downline_level(self, parent_level: str) -> str:
        if parent_level == "strategic":
            return "city"
        return "campus"

    def _validate_downline_level(self, *, parent_level: str, child_level: str) -> None:
        allowed_levels = {
            "admin": {"strategic", "city", "campus"},
            "strategic": {"city", "campus"},
            "city": {"campus"},
            "campus": set(),
        }
        if child_level not in {"strategic", "city", "campus"}:
            raise ValidationError(message="invalid distributor level")
        if child_level not in allowed_levels.get(parent_level, set()):
            raise ValidationError(message="downline level is not allowed for current parent level")

    def _would_create_downline_cycle(self, *, parent_user_id: int, downline_user_id: int) -> bool:
        cursor = parent_user_id
        visited = set()
        while cursor and cursor not in visited:
            visited.add(cursor)
            profile = self.repository.get_profile_for_user(user_id=cursor)
            if profile is None or profile.parent_distributor_id is None:
                return False
            if profile.parent_distributor_id == downline_user_id:
                return True
            cursor = profile.parent_distributor_id
        return False
