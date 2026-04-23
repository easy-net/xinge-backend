from typing import List, Optional

from pydantic import BaseModel


class MPSchoolListReq(BaseModel):
    keyword: Optional[str] = None
    city: Optional[str] = None
    is_985: Optional[bool] = None
    is_211: Optional[bool] = None
    page: int = 1
    page_size: int = 20


class MPSchoolDetailReq(BaseModel):
    school_name: str


class MPMajorItem(BaseModel):
    name: str
    major_type: Optional[str] = None
    major_score: Optional[int] = None


class MPCollegeItem(BaseModel):
    name: str
    college_score: Optional[int] = None
    majors: List[MPMajorItem]

