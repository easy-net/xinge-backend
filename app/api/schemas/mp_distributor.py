from pydantic import BaseModel


class MPPageReq(BaseModel):
    page: int = 1
    page_size: int = 20


class MPDistributorApplyReq(BaseModel):
    phone: str
    real_name: str
    reason: str
    target_level: str
