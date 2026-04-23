from pydantic import BaseModel


class MPUserInfoDoc(BaseModel):
    open_id: str
    user_id: int

