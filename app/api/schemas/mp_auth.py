from typing import Optional

from pydantic import BaseModel


class MPLoginReq(BaseModel):
    distributor_id: Optional[int] = None
    parent_distributor_id: Optional[int] = None
    target_level: Optional[str] = None


class MPBindPhoneReq(BaseModel):
    phone_code: str
