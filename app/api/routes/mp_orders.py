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
    request: Request,
    body: MPCreateOrderReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client, settings=request.app.state.settings).create_order(
        user=user,
        report_id=body.report_id,
        amount=body.amount,
        platform=body.platform or "android",
    )
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/detail")
def order_detail(
    request: Request,
    body: MPOrderDetailReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client, settings=request.app.state.settings).detail(user=user, order_id=body.order_id)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/list")
def order_list(
    request: Request,
    body: MPOrderListReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client, settings=request.app.state.settings).list_orders(user=user, page=body.page, page_size=body.page_size)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/pay")
def order_pay(
    request: Request,
    body: MPOrderPayReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client, settings=request.app.state.settings).repay_order(
        user=user, order_id=body.order_id, platform=body.platform or "android"
    )
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/orders/confirm")
def order_confirm(
    request: Request,
    body: MPOrderConfirmReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client, settings=request.app.state.settings).confirm_paid(
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
