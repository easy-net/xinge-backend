from sqlalchemy import delete

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models.distributor import DistributorApplication, DistributorProfile, DistributorQuotaRecord, DistributorWithdrawal
from app.db.models.message import Message
from app.db.models.order import Order
from app.db.models.report import Report
from app.db.models.user import User
from app.repositories.distributor_repository import DistributorRepository
from app.repositories.user_repository import UserRepository


class AdminUserService:
    def __init__(self, db, settings=None):
        self.db = db
        self.settings = settings
        self.user_repository = UserRepository(db)
        self.distributor_repository = DistributorRepository(db)

    def list_users(self, *, page: int, page_size: int, keyword: str = "", role=None):
        items, total = self.user_repository.list_users_with_total(page=page, page_size=page_size, keyword=keyword, role=role)
        list_items = []
        for item in items:
            profile = self.distributor_repository.get_profile_for_user(user_id=item.id)
            list_items.append(
                {
                    "user_id": item.id,
                    "openid": item.openid,
                    "unionid": item.unionid,
                    "nickname": item.nickname or "",
                    "phone_masked": item.phone_masked or "",
                    "role": item.role,
                    "is_distributor": item.is_distributor,
                    "distributor_level": getattr(profile, "distributor_level", None),
                    "parent_distributor_id": getattr(profile, "parent_distributor_id", None),
                    "quota_total": getattr(profile, "quota_total", 0),
                    "quota_used": getattr(profile, "quota_used", 0),
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

    def create_user(
        self,
        *,
        openid: str,
        unionid: str = "",
        nickname: str = "",
        phone_masked: str = "",
        role: str = "user",
        distributor_level: str = "",
        parent_distributor_id: int = 0,
        quota_total: int = 0,
    ):
        normalized_openid = openid.strip()
        normalized_role = (role or "user").strip().lower()
        if not normalized_openid:
            raise ValidationError(message="openid is required")
        if normalized_role not in {"user", "distributor"}:
            raise ValidationError(message="role must be user or distributor")
        if self.user_repository.get_by_openid(normalized_openid) is not None:
            raise ConflictError(message="openid already exists")

        user = self.user_repository.create_user(openid=normalized_openid, unionid=unionid.strip())
        user.nickname = nickname.strip()
        user.phone_masked = phone_masked.strip()

        if normalized_role == "distributor":
            level = (distributor_level or "campus").strip().lower()
            if level not in {"strategic", "city", "campus"}:
                raise ValidationError(message="invalid distributor level")
            if parent_distributor_id:
                parent = self.user_repository.get_by_id(parent_distributor_id)
                parent_profile = self.distributor_repository.get_profile_for_user(user_id=parent_distributor_id) if parent else None
                if parent is None or parent_profile is None:
                    raise ValidationError(message="parent distributor not found")
                if parent_profile.distributor_level == "campus":
                    raise ValidationError(message="campus distributor cannot manage downlines")
            user.role = "distributor"
            user.is_distributor = True
            self.distributor_repository.create_profile(
                user_id=user.id,
                distributor_level=level,
                parent_distributor_id=parent_distributor_id or None,
                quota_total=max(quota_total, 0),
            )

        self.db.commit()
        return {
            "user_id": user.id,
            "openid": user.openid,
            "role": user.role,
            "is_distributor": user.is_distributor,
            "nickname": user.nickname,
            "phone_masked": user.phone_masked,
            "distributor_level": distributor_level.strip().lower() if normalized_role == "distributor" else None,
            "parent_distributor_id": parent_distributor_id or None,
            "status": "created",
        }

    def delete_user(self, *, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="user not found")
        if user.role == "admin":
            raise ValidationError(message="admin user cannot be deleted")

        profile = self.distributor_repository.get_profile_for_user(user_id=user.id)
        if profile is not None:
            downline_count = self.distributor_repository.count_direct_downlines(parent_distributor_id=user.id)
            if downline_count > 0:
                raise ValidationError(message="user still has direct downlines")

        self.db.execute(delete(Order).where(Order.user_id == user.id))
        self.db.execute(delete(Report).where(Report.user_id == user.id))
        self.db.execute(delete(Message).where(Message.user_id == user.id))
        self.db.execute(delete(DistributorWithdrawal).where(DistributorWithdrawal.user_id == user.id))
        self.db.execute(delete(DistributorApplication).where(DistributorApplication.user_id == user.id))
        self.db.execute(delete(DistributorQuotaRecord).where(DistributorQuotaRecord.user_id == user.id))
        self.db.execute(delete(DistributorQuotaRecord).where(DistributorQuotaRecord.counterparty_user_id == user.id))
        self.db.execute(delete(DistributorProfile).where(DistributorProfile.user_id == user.id))
        self.db.delete(user)
        self.db.commit()
        return {
            "user_id": user_id,
            "status": "deleted",
        }
