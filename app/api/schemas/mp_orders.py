from typing import Optional

from pydantic import BaseModel


class MPCreateOrderReq(BaseModel):
    report_id: int
    amount: int


class MPOrderDetailReq(BaseModel):
    order_id: str


class MPWechatNotifyReq(BaseModel):
    notify_id: str
    order_id: str
    amount: int
    status: str = "success"
    paid_at: Optional[str] = None
