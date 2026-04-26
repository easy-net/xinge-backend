from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.device import UserDevice
from app.db.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_openid(self, openid: str) -> Optional[User]:
        return self.db.execute(select(User).where(User.openid == openid)).scalar_one_or_none()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()

    def list_users(self, *, page: int, page_size: int, exclude_user_id: Optional[int] = None):
        stmt = select(User)
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return self.db.execute(
            stmt.order_by(User.created_at.desc(), User.id.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()

    def create_user(self, *, openid: str, unionid: str = "") -> User:
        user = User(openid=openid, unionid=unionid)
        self.db.add(user)
        self.db.flush()
        return user

    def update_device(self, *, user: User, device_uuid: str, system_version: str) -> UserDevice:
        device = self.db.execute(
            select(UserDevice).where(
                UserDevice.user_id == user.id,
                UserDevice.device_uuid == device_uuid,
            )
        ).scalar_one_or_none()
        if device is None:
            device = UserDevice(
                user_id=user.id,
                device_uuid=device_uuid,
                system_version=system_version,
                last_login_at=datetime.utcnow(),
            )
            self.db.add(device)
        else:
            device.system_version = system_version
            device.last_login_at = datetime.utcnow()
        self.db.flush()
        return device

    def update_phone(self, *, user: User, phone_ciphertext: str, phone_masked: str) -> User:
        user.phone_ciphertext = phone_ciphertext
        user.phone_masked = phone_masked
        self.db.flush()
        return user

    def update_profile(self, *, user: User, nickname=None, avatar_url=None) -> User:
        if nickname is not None:
            user.nickname = nickname
        if avatar_url is not None:
            user.avatar_url = avatar_url
        self.db.flush()
        return user
