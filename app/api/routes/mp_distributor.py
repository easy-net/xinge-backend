import json

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, get_wechat_pay_client
from app.api.schemas.mp_distributor import (
    MPAllocateQuotaReq,
    MPDistributorCommissionsReq,
    MPDistributorApplyReq,
    MPDistributorWithdrawStatusReq,
    MPDistributorWithdrawReq,
    MPDownlinesReq,
    MPPageReq,
)
from app.core.response import mp_response
from app.services.distributor_service import DistributorService

router = APIRouter(tags=["mp/distributor"])


def _distributor_service(request: Request, db: Session) -> DistributorService:
    return DistributorService(db, get_wechat_pay_client(request), request.app.state.settings)


@router.post("/mp/distributor/apply")
def distributor_apply(
    request: Request,
    body: MPDistributorApplyReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = _distributor_service(request, db).apply(user=user, payload=body.model_dump())
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/me")
def distributor_me(
    request: Request,
    body: dict = Body(default_factory=dict),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    del body
    user, _ = current
    data = _distributor_service(request, db).me(user=user)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/application/status")
def distributor_application_status(
    request: Request,
    body: dict = Body(default_factory=dict),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    del body
    user, _ = current
    data = _distributor_service(request, db).application_status(user=user)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/withdrawals")
def distributor_withdrawals(
    request: Request,
    body: MPPageReq = Body(default_factory=MPPageReq),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = _distributor_service(request, db).list_withdrawals(user=user, page=body.page, page_size=body.page_size)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/withdraw")
def distributor_withdraw(
    request: Request,
    body: MPDistributorWithdrawReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = _distributor_service(request, db).create_withdrawal(user=user, amount=body.amount)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/withdrawals/status")
def distributor_withdrawal_status(
    request: Request,
    body: MPDistributorWithdrawStatusReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = _distributor_service(request, db).refresh_withdrawal_status(user=user, withdraw_id=body.withdraw_id)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/downlines")
def distributor_downlines(
    request: Request,
    body: MPDownlinesReq = Body(default_factory=MPDownlinesReq),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = _distributor_service(request, db).list_downlines(
        user=user,
        page=body.page,
        page_size=body.page_size,
        level=body.level,
    )
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/quota/allocate")
def distributor_allocate_quota(
    request: Request,
    body: MPAllocateQuotaReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = _distributor_service(request, db).allocate_quota(
        user=user,
        downline_user_id=body.downline_user_id,
        amount=body.amount,
    )
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/quota/records")
def distributor_quota_records(
    request: Request,
    body: MPPageReq = Body(default_factory=MPPageReq),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = _distributor_service(request, db).list_quota_records(user=user, page=body.page, page_size=body.page_size)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/commissions")
def distributor_commissions(
    request: Request,
    body: MPDistributorCommissionsReq = Body(default_factory=MPDistributorCommissionsReq),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = _distributor_service(request, db).list_commissions(user=user, page=body.page, page_size=body.page_size)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/distributor/withdrawals/notify/wechat")
async def wechat_transfer_notify(
    request: Request,
    db: Session = Depends(get_db_session),
):
    """微信支付转账结果异步回调
    
    处理商家转账到零钱的异步通知，更新提现状态
    """
    raw_body = await request.body()
    body_text = raw_body.decode("utf-8") if raw_body else ""
    try:
        payload = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        payload = {}
    
    # 如果是微信支付 V3 回调，验证签名
    wechat_pay_client = get_wechat_pay_client(request)
    if payload.get("resource") and wechat_pay_client:
        try:
            payload["_headers"] = dict(request.headers)
            payload["_raw_body"] = body_text
            if hasattr(wechat_pay_client, "verify_callback_signature"):
                wechat_pay_client.verify_callback_signature(dict(request.headers), body_text)
            decrypted = wechat_pay_client.decrypt_callback_resource(payload["resource"])
            transfer_bill_no = decrypted.get("transfer_bill_no", "")
            out_bill_no = decrypted.get("out_bill_no", "")
            state = decrypted.get("state", "")
            fail_reason = decrypted.get("fail_reason", "")
        except Exception as e:
            return {"code": "FAIL", "message": str(e)}
    else:
        transfer_bill_no = payload.get("transfer_bill_no", "")
        out_bill_no = payload.get("out_bill_no", "")
        state = payload.get("state", "")
        fail_reason = payload.get("fail_reason", "")
    
    # 处理回调
    try:
        result = DistributorService(db, wechat_pay_client, request.app.state.settings).handle_transfer_callback(
            transfer_bill_no=transfer_bill_no,
            state=state,
            out_bill_no=out_bill_no,
            fail_reason=fail_reason,
        )
        return {"code": "SUCCESS", "data": result}
    except Exception as e:
        return {"code": "FAIL", "message": str(e)}
