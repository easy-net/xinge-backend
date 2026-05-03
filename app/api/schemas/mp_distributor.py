from typing import Optional

from pydantic import BaseModel


class MPPageReq(BaseModel):
    page: int = 1
    page_size: int = 20


class MPDistributorApplyReq(BaseModel):
    phone: str
    real_name: str
    reason: str
    target_level: str


class MPDownlinesReq(BaseModel):
    level: Optional[str] = None
    page: int = 1
    page_size: int = 20


class MPAllocateQuotaReq(BaseModel):
    downline_user_id: int
    amount: int


class MPDistributorWithdrawReq(BaseModel):
    amount: int


class MPDistributorWithdrawStatusReq(BaseModel):
    withdraw_id: str


class MPDistributorCommissionsReq(BaseModel):
    page: int = 1
    page_size: int = 20
