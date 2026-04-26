from pydantic import BaseModel


class MPPageReq(BaseModel):
    page: int = 1
    page_size: int = 20
