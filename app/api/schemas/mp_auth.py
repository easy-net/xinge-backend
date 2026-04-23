from typing import Optional

from pydantic import BaseModel


class MPLoginReq(BaseModel):
    distributor_id: Optional[int] = None


class MPBindPhoneReq(BaseModel):
    phone_code: str

