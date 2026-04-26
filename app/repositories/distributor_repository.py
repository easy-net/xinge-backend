from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.distributor import DistributorApplication, DistributorProfile, DistributorWithdrawal


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

    def count_direct_downlines(self, *, parent_distributor_id: int, distributor_level: Optional[str] = None) -> int:
        stmt = select(func.count(DistributorProfile.id)).where(DistributorProfile.parent_distributor_id == parent_distributor_id)
        if distributor_level is not None:
            stmt = stmt.where(DistributorProfile.distributor_level == distributor_level)
        return self.db.execute(stmt).scalar_one()
