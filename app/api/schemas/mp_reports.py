from typing import List, Optional

from pydantic import BaseModel, Field


class MPPageReq(BaseModel):
    page: int = 1
    page_size: int = 20


class MPReportIDReq(BaseModel):
    report_id: int


class MPCreateReportReq(BaseModel):
    name: str
    school_name: Optional[str] = None
    college_name: Optional[str] = None
    major_name: Optional[str] = None
    gender: Optional[str] = None
    gaokao_province: Optional[str] = None
    gaokao_score: Optional[int] = None
    gaokao_rank: Optional[int] = None
    enrollment_year: Optional[int] = None
    chinese_score: Optional[int] = None
    math_score: Optional[int] = None
    english_score: Optional[int] = None
    physics_score: Optional[int] = None
    chemistry_score: Optional[int] = None
    biology_score: Optional[int] = None
    english_level: Optional[str] = None
    hukou: Optional[str] = None
    major_satisfaction: Optional[str] = None
    employment_intention: List[str] = Field(default_factory=list)
    study_intention: Optional[str] = None
    study_path_priority: List[str] = Field(default_factory=list)
    target_major: List[str] = Field(default_factory=list)
    target_work_city: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
