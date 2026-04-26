from fastapi import APIRouter, Query, Request

from app.core.response import public_response

router = APIRouter(tags=["admin/finance"])


@router.get("/admin/wechat-pay/balances")
def admin_get_wechat_pay_balances(
    request: Request,
    focus: str = Query("OPERATION", pattern="^(BASIC|OPERATION|FEES)$"),
):
    client = request.app.state.wechat_pay_client
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
