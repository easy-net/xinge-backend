import logging
from datetime import datetime

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models.message import Message
from app.repositories.distributor_repository import DistributorRepository
from app.repositories.report_repository import ReportRepository


class DistributorService:
    def __init__(self, db):
        self.db = db
        self.repository = DistributorRepository(db)
        self.report_repository = ReportRepository(db)

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

    def list_withdrawals(self, *, user, page: int, page_size: int):
        self._require_distributor(user)
        items, total = self.repository.list_withdrawals_for_user(user_id=user.id, page=page, page_size=page_size)
        return {
            "list": [
                {
                    "amount": item.amount,
                    "bank_account_masked": item.bank_account_masked,
                    "bank_name": item.bank_name,
                    "completed_at": item.completed_at.isoformat() + "Z" if item.completed_at else None,
                    "created_at": item.created_at.isoformat() + "Z",
                    "status": item.status,
                    "withdraw_id": item.withdraw_id,
                }
                for item in items
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

    def _require_pending_application(self, application_id: str):
        application = self.repository.get_application_by_application_id(application_id=application_id)
        if application is None:
            raise NotFoundError(message="application not found")
        if application.status != "pending":
            raise ConflictError(message="application is already reviewed")
        return application

    def _default_quota_for_level(self, distributor_level: str) -> int:
        defaults = {
            "strategic": 500,
            "city": 200,
            "campus": 50,
        }
        return defaults.get(distributor_level, 0)
