from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.api.schemas.mp_distributor import MPPageReq
from app.core.response import mp_response
from app.services.distributor_service import DistributorService

router = APIRouter(tags=["mp/distributor"])


@router.post("/mp/distributor/me")
def distributor_me(
    body: dict = Body(default_factory=dict),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    del body
    user, _ = current
    data = DistributorService(db).me(user=user)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/application/status")
def distributor_application_status(
    body: dict = Body(default_factory=dict),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    del body
    user, _ = current
    data = DistributorService(db).application_status(user=user)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/withdrawals")
def distributor_withdrawals(
    body: MPPageReq = Body(default_factory=MPPageReq),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = DistributorService(db).list_withdrawals(user=user, page=body.page, page_size=body.page_size)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})
