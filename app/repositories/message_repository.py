from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_unread_for_user(self, user_id: int) -> int:
        stmt = select(func.count(Message.id)).where(and_(Message.user_id == user_id, Message.is_read.is_(False)))
        return self.db.execute(stmt).scalar_one()

    def list_for_user(self, *, user_id: int, page: int, page_size: int, is_read=None):
        stmt = select(Message).where(Message.user_id == user_id)
        if is_read is not None:
            stmt = stmt.where(Message.is_read == is_read)
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        items = self.db.execute(
            stmt.order_by(Message.created_at.desc(), Message.id.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return items, total

    def get_for_user(self, *, message_id: int, user_id: int):
        stmt = select(Message).where(and_(Message.id == message_id, Message.user_id == user_id))
        return self.db.execute(stmt).scalar_one_or_none()

    def mark_read(self, *, message: Message):
        message.is_read = True
        self.db.flush()
        return message

