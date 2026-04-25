from app.core.errors import NotFoundError
from app.repositories.message_repository import MessageRepository


class MessageService:
    def __init__(self, db):
        self.db = db
        self.repository = MessageRepository(db)

    def list_messages(self, *, user, page: int, page_size: int, is_read=None):
        items, total = self.repository.list_for_user(
            user_id=user.id,
            page=page,
            page_size=page_size,
            is_read=is_read,
        )
        return {
            "list": [
                {
                    "content": item.content,
                    "created_at": item.created_at.isoformat() + "Z",
                    "is_read": item.is_read,
                    "message_id": item.id,
                    "title": item.title,
                    "type": item.type,
                }
                for item in items
            ],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def read_message(self, *, user, message_id: int):
        message = self.repository.get_for_user(message_id=message_id, user_id=user.id)
        if message is None:
            raise NotFoundError(message="message not found")
        self.repository.mark_read(message=message)
        self.db.commit()
        return {
            "is_read": message.is_read,
            "message_id": message.id,
        }
