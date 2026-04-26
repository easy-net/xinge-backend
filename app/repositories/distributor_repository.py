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

    def count_direct_downlines(self, *, parent_distributor_id: int, distributor_level: str | None = None) -> int:
        stmt = select(func.count(DistributorProfile.id)).where(DistributorProfile.parent_distributor_id == parent_distributor_id)
        if distributor_level is not None:
            stmt = stmt.where(DistributorProfile.distributor_level == distributor_level)
        return self.db.execute(stmt).scalar_one()
