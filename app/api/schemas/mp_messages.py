from typing import Optional

from pydantic import BaseModel


class MPListMessagesReq(BaseModel):
    page: int = 1
    page_size: int = 20
    is_read: Optional[bool] = None


class MPReadMessageReq(BaseModel):
    message_id: int
