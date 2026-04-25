from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.api.schemas.mp_messages import MPListMessagesReq, MPReadMessageReq
from app.core.response import mp_response
from app.services.message_service import MessageService

router = APIRouter(tags=["mp/messages"])


@router.post("/mp/messages/list")
def list_messages(
    body: MPListMessagesReq = Body(default_factory=MPListMessagesReq),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = MessageService(db).list_messages(user=user, page=body.page, page_size=body.page_size, is_read=body.is_read)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/messages/read")
def read_message(
    body: MPReadMessageReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = MessageService(db).read_message(user=user, message_id=body.message_id)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})
