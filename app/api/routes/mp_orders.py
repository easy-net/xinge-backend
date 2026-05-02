import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, get_wechat_pay_client
from app.api.schemas.mp_orders import (
    MPCreateOrderReq,
    MPOrderConfirmReq,
    MPOrderDetailReq,
    MPOrderListReq,
    MPOrderPayReq,
)
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


@router.post("/mp/orders/list")
def order_list(
    body: MPOrderListReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client).list_orders(user=user, page=body.page, page_size=body.page_size)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/pay")
def order_pay(
    body: MPOrderPayReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client).repay_order(user=user, order_id=body.order_id)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/confirm")
def order_confirm(
    body: MPOrderConfirmReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client).confirm_paid(
        user=user,
        order_id=body.order_id,
        paid_at=body.paid_at or "",
    )
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/notify/wechat")
async def wechat_notify(
    request: Request,
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    raw_body = await request.body()
    body_text = raw_body.decode("utf-8") if raw_body else ""
    try:
        payload = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        payload = {}
    if payload.get("resource"):
        payload["_headers"] = dict(request.headers)
        payload["_raw_body"] = body_text
    return PaymentNotifyService(db, wechat_pay_client).process(payload)
