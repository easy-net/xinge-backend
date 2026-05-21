import json
import xml.etree.ElementTree as ET

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
from app.services.xpay_goods_service import XPayGoodsService

router = APIRouter(tags=["mp/orders"])


def _parse_notify_payload(body_text: str) -> dict:
    if not body_text:
        return {}
    try:
        return json.loads(body_text)
    except json.JSONDecodeError:
        pass
    try:
        root = ET.fromstring(body_text)
    except ET.ParseError:
        return {}
    return {child.tag: child.text or "" for child in root}


def _is_xpay_goods_notify(payload: dict) -> bool:
    event = payload.get("Event") or payload.get("event") or payload.get("MsgType")
    return event == "xpay_goods_deliver_notify"


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


@router.post("/mp/orders/virtual")
def create_virtual_order(
    request: Request,
    body: MPCreateOrderReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client, settings=request.app.state.settings).create_virtual_order(
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


@router.post("/mp/orders/virtual_confirm")
def order_virtual_confirm(
    request: Request,
    body: MPOrderConfirmReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_pay_client=Depends(get_wechat_pay_client),
):
    user, _ = current
    data = OrderService(db, wechat_pay_client, settings=request.app.state.settings).confirm_virtual_paid(
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
    payload = _parse_notify_payload(body_text)
    if _is_xpay_goods_notify(payload):
        pay_sig = request.query_params.get("pay_sig", "")
        if pay_sig:
            wechat_pay_client.verify_virtual_notify_signature(body_text=body_text, pay_sig=pay_sig)
        return XPayGoodsService(db, wechat_pay_client).process_goods_deliver_notify(payload)
    if payload.get("resource"):
        payload["_headers"] = dict(request.headers)
        payload["_raw_body"] = body_text
    return PaymentNotifyService(db, wechat_pay_client).process(payload)
