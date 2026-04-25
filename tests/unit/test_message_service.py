from app.db.models.message import Message
from app.db.models.user import User
from app.services.message_service import MessageService


class UserStub:
    def __init__(self, user_id):
        self.id = user_id


def seed_user_and_message(db_session):
    user = User(openid="openid-msg-1", unionid="unionid-msg-1")
    db_session.add(user)
    db_session.flush()
    db_session.add(
        Message(
            user_id=user.id,
            type="system",
            title="欢迎使用",
            content="欢迎来到系统",
            is_read=False,
        )
    )
    db_session.commit()
    return user


def test_read_message_marks_it_read(db_session):
    user = seed_user_and_message(db_session)
    service = MessageService(db_session)
    list_data = service.list_messages(user=UserStub(user.id), page=1, page_size=20)

    result = service.read_message(user=UserStub(user.id), message_id=list_data["list"][0]["message_id"])

    assert result["is_read"] is True

