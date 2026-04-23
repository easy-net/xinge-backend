from pydantic import BaseModel


class MPPriceDoc(BaseModel):
    currency: str
    current_amount: int
    current_amount_display: str
    description: str
    discount_rate: float
    is_limited_time: bool
    limited_time_end: str
    original_amount: int
    original_amount_display: str


class MPUserStatsDoc(BaseModel):
    display_count: int
    display_text: str

