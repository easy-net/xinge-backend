from typing import Optional

from pydantic import BaseModel


class MPUpdateMeReq(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

