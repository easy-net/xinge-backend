from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.distributor import DistributorApplication, DistributorProfile, DistributorQuotaRecord, DistributorWithdrawal
from app.db.models.user import User


class DistributorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_profile_for_user(self, *, user_id: int):
        stmt = select(DistributorProfile).where(DistributorProfile.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_application_for_user(self, *, user_id: int):
        stmt = (
            select(DistributorApplication)
            .where(DistributorApplication.user_id == user_id)
            .order_by(DistributorApplication.created_at.desc(), DistributorApplication.id.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def create_application(self, *, user_id: int, application_id: str, real_name: str, phone: str, reason: str, target_level: str):
        application = DistributorApplication(
            application_id=application_id,
            user_id=user_id,
            real_name=real_name,
            phone=phone,
            reason=reason,
            target_level=target_level,
            status="pending",
        )
        self.db.add(application)
        self.db.flush()
        return application

    def get_application_by_application_id(self, *, application_id: str):
        stmt = select(DistributorApplication).where(DistributorApplication.application_id == application_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_applications(self, *, page: int, page_size: int, status: Optional[str] = None):
        stmt = select(DistributorApplication)
        if status:
            stmt = stmt.where(DistributorApplication.status == status)
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        items = self.db.execute(
            stmt
            .order_by(DistributorApplication.created_at.desc(), DistributorApplication.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return items, total

    def update_application_status(self, *, application: DistributorApplication, status: str, reject_reason: str = ""):
        application.status = status
        application.reject_reason = reject_reason
        self.db.flush()
        return application

    def create_profile(
        self,
        *,
        user_id: int,
        distributor_level: str,
        parent_distributor_id: Optional[int] = None,
        quota_total: int = 0,
    ):
        profile = DistributorProfile(
            user_id=user_id,
            distributor_level=distributor_level,
            parent_distributor_id=parent_distributor_id,
            quota_total=quota_total,
        )
        self.db.add(profile)
        self.db.flush()
        return profile

    def list_withdrawals_for_user(self, *, user_id: int, page: int, page_size: int):
        base_stmt = select(DistributorWithdrawal).where(DistributorWithdrawal.user_id == user_id)
        total = self.db.execute(select(func.count()).select_from(base_stmt.subquery())).scalar_one()
        items = self.db.execute(
            base_stmt
            .order_by(DistributorWithdrawal.created_at.desc(), DistributorWithdrawal.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return items, total

    def list_withdrawals(self, *, page: int, page_size: int, status: Optional[str] = None):
        stmt = select(DistributorWithdrawal, User).join(User, User.id == DistributorWithdrawal.user_id)
        if status:
            stmt = stmt.where(DistributorWithdrawal.status == status)
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        items = self.db.execute(
            stmt
            .order_by(DistributorWithdrawal.created_at.desc(), DistributorWithdrawal.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, total

    def create_withdrawal(
        self,
        *,
        user_id: int,
        withdraw_id: str,
        amount: int,
        account_name: str,
        bank_name: str,
        bank_account_masked: str,
        transfer_bill_no: str = "",
        fail_reason: str = "",
        status: str = "pending",
    ):
        record = DistributorWithdrawal(
            user_id=user_id,
            withdraw_id=withdraw_id,
            amount=amount,
            account_name=account_name,
            bank_name=bank_name,
            bank_account_masked=bank_account_masked,
            transfer_bill_no=transfer_bill_no,
            fail_reason=fail_reason,
            status=status,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def get_withdrawal_by_withdraw_id(self, *, withdraw_id: str):
        stmt = select(DistributorWithdrawal).where(DistributorWithdrawal.withdraw_id == withdraw_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_withdrawal_by_transfer_bill_no(self, *, transfer_bill_no: str):
        stmt = select(DistributorWithdrawal).where(DistributorWithdrawal.transfer_bill_no == transfer_bill_no)
        return self.db.execute(stmt).scalar_one_or_none()

    def update_withdrawal_status(
        self,
        *,
        withdrawal: DistributorWithdrawal,
        status: str,
        completed_at=None,
        transfer_bill_no: str = "",
        fail_reason: str = "",
    ):
        withdrawal.status = status
        withdrawal.completed_at = completed_at
        if transfer_bill_no:
            withdrawal.transfer_bill_no = transfer_bill_no
        withdrawal.fail_reason = fail_reason or ""
        self.db.flush()
        return withdrawal

    def count_direct_downlines(self, *, parent_distributor_id: int, distributor_level: Optional[str] = None) -> int:
        stmt = select(func.count(DistributorProfile.id)).where(DistributorProfile.parent_distributor_id == parent_distributor_id)
        if distributor_level is not None:
            stmt = stmt.where(DistributorProfile.distributor_level == distributor_level)
        return self.db.execute(stmt).scalar_one()

    def list_direct_downlines(self, *, parent_distributor_id: int, page: int, page_size: int, distributor_level: Optional[str] = None):
        stmt = (
            select(DistributorProfile, User)
            .join(User, User.id == DistributorProfile.user_id)
            .where(DistributorProfile.parent_distributor_id == parent_distributor_id)
        )
        if distributor_level is not None:
            stmt = stmt.where(DistributorProfile.distributor_level == distributor_level)
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        items = self.db.execute(
            stmt
            .order_by(DistributorProfile.created_at.desc(), DistributorProfile.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, total

    def list_profiles(self, *, page: int, page_size: int, distributor_level: Optional[str] = None):
        stmt = select(DistributorProfile, User).join(User, User.id == DistributorProfile.user_id)
        if distributor_level is not None:
            stmt = stmt.where(DistributorProfile.distributor_level == distributor_level)
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        items = self.db.execute(
            stmt
            .order_by(DistributorProfile.created_at.desc(), DistributorProfile.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, total

    def create_quota_record(
        self,
        *,
        user_id: int,
        direction: str,
        counterparty_user_id: Optional[int],
        counterparty_level: str,
        amount: int,
        quota_before: int,
        quota_after: int,
        remark: str,
    ):
        record = DistributorQuotaRecord(
            user_id=user_id,
            direction=direction,
            counterparty_user_id=counterparty_user_id,
            counterparty_level=counterparty_level,
            amount=amount,
            quota_before=quota_before,
            quota_after=quota_after,
            remark=remark,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def list_quota_records_for_user(self, *, user_id: int, page: int, page_size: int):
        stmt = (
            select(DistributorQuotaRecord, User)
            .outerjoin(User, User.id == DistributorQuotaRecord.counterparty_user_id)
            .where(DistributorQuotaRecord.user_id == user_id)
        )
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        items = self.db.execute(
            stmt
            .order_by(DistributorQuotaRecord.created_at.desc(), DistributorQuotaRecord.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, total
