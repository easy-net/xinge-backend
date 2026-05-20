from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_wechat_pay_client
from app.core.response import public_response
from app.repositories.order_repository import OrderRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository

router = APIRouter(tags=["admin/finance"])


@router.get("/admin/wechat-pay/balances")
def admin_get_wechat_pay_balances(
    focus: str = Query("OPERATION", pattern="^(BASIC|OPERATION|FEES)$"),
    client=Depends(get_wechat_pay_client),
):
    account_types = ["OPERATION", "BASIC", "FEES"]
    balances = {}
    for account_type in account_types:
        result = client.query_balance(account_type=account_type)
        balances[account_type] = {
            "account_type": result.account_type,
            "available_amount": result.available_amount,
            "pending_amount": result.pending_amount,
        }
    return public_response(
        {
            "focus": focus,
            "balances": balances,
        }
    )


@router.get("/admin/xpay/orders/query")
def admin_query_xpay_order(
    order_id: str = Query(..., min_length=1),
    openid: str = Query("", min_length=0),
    db: Session = Depends(get_db_session),
    client=Depends(get_wechat_pay_client),
):
    normalized_order_id = order_id.strip()
    normalized_openid = openid.strip()
    result = client.query_virtual_order(order_id=normalized_order_id, openid=normalized_openid)

    order = OrderRepository(db).get_by_order_id(order_id=normalized_order_id)
    report = None
    user = None
    if order is not None:
        report = ReportRepository(db).get_for_user(report_id=order.report_id, user_id=order.user_id)
        user = UserRepository(db).get_by_id(order.user_id)

    local_order = None
    if order is not None:
        local_order = {
            "amount": order.amount,
            "channel": order.channel,
            "created_at": order.created_at.isoformat() + "Z",
            "order_id": order.order_id,
            "paid_at": order.paid_at or None,
            "report_id": order.report_id,
            "status": order.status,
            "user_id": order.user_id,
        }

    return public_response(
        {
            "query": {
                "order_id": normalized_order_id,
                "openid": normalized_openid,
            },
            "xpay_order": {
                "amount": result.amount,
                "is_paid": result.is_paid,
                "order_id": result.order_id,
                "paid_at": result.paid_at,
                "raw": result.raw or {},
                "status": result.status,
                "wx_order_id": result.wx_order_id,
            },
            "local_order": local_order,
            "report": {
                "report_id": report.id,
                "name": report.name,
                "school_name": (report.form_data or {}).get("school_name", ""),
                "status": report.status,
            } if report is not None else None,
            "user": {
                "user_id": user.id,
                "openid": user.openid,
                "nickname": user.nickname,
                "phone_masked": user.phone_masked,
            } if user is not None else None,
        }
    )
