import logging

from app.core.errors import ForbiddenError, NotFoundError
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
