from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, get_wechat_pay_client
from app.api.schemas.mp_orders import MPCreateOrderReq, MPOrderDetailReq, MPWechatNotifyReq
from app.core.response import mp_response
from app.services.order_service import OrderService
from app.services.payment_notify_service import PaymentNotifyService

router = APIRouter(tags=["mp/orders"])


@router.post("/mp/orders")
def create_order(
    body: MPCreateOrderReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client).create_order(
        user=user,
        report_id=body.report_id,
        amount=body.amount,
    )
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/detail")
def order_detail(
    body: MPOrderDetailReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client).detail(user=user, order_id=body.order_id)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/notify/wechat")
def wechat_notify(
    body: MPWechatNotifyReq,
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    return PaymentNotifyService(db, wechat_pay_client).process(body.model_dump())
