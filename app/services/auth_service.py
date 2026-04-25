from app.core.config import get_settings
from app.core.errors import AuthError
from app.core.security import encrypt_text, mask_phone
from app.repositories.message_repository import MessageRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db, wechat_auth_client):
        self.db = db
        self.wechat_auth_client = wechat_auth_client
        self.user_repository = UserRepository(db)
        self.report_repository = ReportRepository(db)
        self.message_repository = MessageRepository(db)

    def login(self, request_context, distributor_id=None):
        session_info = self.wechat_auth_client.code_to_session(request_context.login_code)
        user = self.user_repository.get_by_openid(session_info.openid)
        is_new_user = False
        if user is None:
            user = self.user_repository.create_user(openid=session_info.openid, unionid=session_info.unionid)
            is_new_user = True

        self.user_repository.update_device(
            user=user,
            device_uuid=request_context.device_uuid,
            system_version=request_context.system_version,
        )
        self.db.commit()

        data = {
            "has_phone": bool(user.phone_masked),
            "is_new_user": is_new_user,
            "role": "distributor" if user.is_distributor else "user",
            "user_info": {
                "open_id": user.openid,
                "user_id": user.id,
            },
        }
        return data, {"open_id": user.openid, "user_id": user.id}

    def bind_phone(self, request_context, phone_code: str):
        session_info = self.wechat_auth_client.code_to_session(request_context.login_code)
        user = self.user_repository.get_by_openid(session_info.openid)
        if user is None:
            raise AuthError(message="unauthorized")
        phone = self.wechat_auth_client.decrypt_phone_number(phone_code)
        settings = get_settings()
        phone_ciphertext = encrypt_text(phone, settings.encryption_key)
        phone_masked = mask_phone(phone)
        self.user_repository.update_phone(user=user, phone_ciphertext=phone_ciphertext, phone_masked=phone_masked)
        self.user_repository.update_device(
            user=user,
            device_uuid=request_context.device_uuid,
            system_version=request_context.system_version,
        )
        self.db.commit()
        return {"phone_masked": phone_masked}, {"open_id": user.openid, "user_id": user.id}

    def me(self, user, request_context):
        self.user_repository.update_device(
            user=user,
            device_uuid=request_context.device_uuid,
            system_version=request_context.system_version,
        )
        self.db.commit()
        data = {
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() + "Z",
            "distributor_level": None,
            "has_phone": bool(user.phone_masked),
            "is_distributor": user.is_distributor,
            "nickname": user.nickname,
            "parent_distributor_id": None,
            "phone_masked": user.phone_masked or None,
            "report_count": self.report_repository.count_for_user(user.id),
            "role": "distributor" if user.is_distributor else "user",
            "unread_message_count": self.message_repository.count_unread_for_user(user.id),
            "user_id": user.id,
        }
        return data, {"open_id": user.openid, "user_id": user.id}

    def update_me(self, user, request_context, *, nickname=None, avatar_url=None):
        self.user_repository.update_profile(user=user, nickname=nickname, avatar_url=avatar_url)
        self.user_repository.update_device(
            user=user,
            device_uuid=request_context.device_uuid,
            system_version=request_context.system_version,
        )
        self.db.commit()
        return {"user_id": user.id}, {"open_id": user.openid, "user_id": user.id}
