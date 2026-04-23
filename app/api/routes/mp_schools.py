from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.api.schemas.mp_schools import MPSchoolDetailReq, MPSchoolListReq
from app.core.response import public_response
from app.services.school_service import SchoolService

router = APIRouter(tags=["mp/schools"])


@router.post("/mp/schools/list")
def school_list(
    body: MPSchoolListReq,
    db: Session = Depends(get_db_session),
):
    data = SchoolService(db).search(body)
    return public_response(data=data)


@router.post("/mp/schools/detail")
def school_detail(
    body: MPSchoolDetailReq,
    db: Session = Depends(get_db_session),
):
    data = SchoolService(db).detail(body.school_name)
    return public_response(data=data)

