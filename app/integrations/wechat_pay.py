import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.errors import ValidationError


@dataclass
class PaymentParams:
    timeStamp: str
    nonceStr: str
    package: str
    signType: str
    paySign: str
    prepay_id: str


@dataclass
class PaymentNotification:
    notify_id: str
    order_id: str
    amount: int
    status: str
    paid_at: str


@dataclass
class TransferResult:
    out_bill_no: str
    transfer_bill_no: str
    state: str
    package_info: str = ""
    fail_reason: str = ""


@dataclass
class BalanceResult:
    account_type: str
    available_amount: int
    pending_amount: int = 0


class WechatPayClient:
    def create_prepay(self, *, order_id: str, amount: int, openid: str) -> PaymentParams:
        raise NotImplementedError

    def parse_notification(self, payload: dict) -> PaymentNotification:
        raise NotImplementedError

    def transfer_to_balance(self, *, out_bill_no: str, amount: int, openid: str, user_name: str = "") -> TransferResult:
        raise NotImplementedError

    def query_transfer_bill(self, *, out_bill_no: str) -> TransferResult:
        raise NotImplementedError

    def query_balance(self, *, account_type: str) -> BalanceResult:
        raise NotImplementedError


class RealWechatPayClient(WechatPayClient):
    PAY_JSAPI_URL = "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi"
    TRANSFER_TO_BALANCE_URL = "https://api.mch.weixin.qq.com/v3/fund-app/mch-transfer/transfer-bills"
    QUERY_TRANSFER_BILL_URL = "https://api.mch.weixin.qq.com/v3/fund-app/mch-transfer/transfer-bills/out-bill-no/{out_bill_no}"
    BALANCE_URL_TEMPLATE = "https://api.mch.weixin.qq.com/v3/merchant/fund/balance/{account_type}"

    def __init__(self, settings):
        self.settings = settings
        self.private_key = None
        self.platform_public_key = None
        if settings.wechat_private_key_path:
            with open(settings.wechat_private_key_path, "rb") as file:
                self.private_key = serialization.load_pem_private_key(file.read(), password=None)
        if settings.wechat_platform_cert_path:
            with open(settings.wechat_platform_cert_path, "rb") as file:
                pem_bytes = file.read()
            try:
                cert = x509.load_pem_x509_certificate(pem_bytes)
                self.platform_public_key = cert.public_key()
            except ValueError:
                self.platform_public_key = serialization.load_pem_public_key(pem_bytes)

    def _nonce(self) -> str:
        return uuid.uuid4().hex

    def _timestamp(self) -> str:
        return str(int(time.time()))

    def _sign_message(self, message: str) -> str:
        if not self.private_key:
            raise RuntimeError("missing merchant private key")
        signature = self.private_key.sign(
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _build_authorization(self, method: str, url_path: str, body_text: str) -> str:
        nonce_str = self._nonce()
        timestamp = self._timestamp()
        message = f"{method}\n{url_path}\n{timestamp}\n{nonce_str}\n{body_text}\n"
        signature = self._sign_message(message)
        return (
            "WECHATPAY2-SHA256-RSA2048 "
            f'mchid="{self.settings.wechat_mch_id}",'
            f'nonce_str="{nonce_str}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{self.settings.wechat_serial_no}"'
        )

    def _request_json(self, *, method: str, url: str, url_path: str, body_text: str = "") -> dict:
        request_method = getattr(requests, method.lower())
        authorization = self._build_authorization(method, url_path, body_text)
        response = request_method(
            url,
            data=body_text.encode("utf-8") if body_text else None,
            timeout=15,
            headers={
                "Authorization": authorization,
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ValidationError(message=self._build_transfer_error_message(response)) from exc
        return response.json()

    def _build_pay_sign(self, prepay_id: str) -> dict[str, str]:
        timestamp = self._timestamp()
        nonce_str = self._nonce()
        package = f"prepay_id={prepay_id}"
        sign_type = "RSA"
        message = f"{self.settings.wechat_app_id}\n{timestamp}\n{nonce_str}\n{package}\n"
        pay_sign = self._sign_message(message)
        return {
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": package,
            "signType": sign_type,
            "paySign": pay_sign,
        }

    def create_prepay(self, *, order_id: str, amount: int, openid: str) -> PaymentParams:
        logger = logging.getLogger(__name__)
        payload = {
            "appid": self.settings.wechat_app_id,
            "mchid": self.settings.wechat_mch_id,
            "description": "信鸽通大学AI规划报告",
            "out_trade_no": order_id,
            "notify_url": self.settings.wechat_notify_url,
            "amount": {
                "total": int(amount),
                "currency": "CNY",
            },
            "payer": {
                "openid": openid,
            },
        }
        body_text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        logger.info(
            "wechat.pay.jsapi.request order_id=%s endpoint=%s mchid=%s appid=%s total=%s has_openid=%s notify_url=%s",
            order_id,
            self.PAY_JSAPI_URL,
            self.settings.wechat_mch_id,
            self.settings.wechat_app_id,
            payload["amount"]["total"],
            bool(openid),
            self.settings.wechat_notify_url,
        )
        data = self._request_json(
            method="POST",
            url=self.PAY_JSAPI_URL,
            url_path="/v3/pay/transactions/jsapi",
            body_text=body_text,
        )
        prepay_id = data["prepay_id"]
        payment_params = self._build_pay_sign(prepay_id)
        logger.info(
            "wechat.pay.jsapi.success order_id=%s prepay_id=%s sign_type=%s package=%s",
            order_id,
            prepay_id,
            payment_params["signType"],
            payment_params["package"],
        )
        return PaymentParams(
            timeStamp=payment_params["timeStamp"],
            nonceStr=payment_params["nonceStr"],
            package=payment_params["package"],
            signType=payment_params["signType"],
            paySign=payment_params["paySign"],
            prepay_id=prepay_id,
        )

    def transfer_to_balance(self, *, out_bill_no: str, amount: int, openid: str, user_name: str = "") -> TransferResult:
        logger = logging.getLogger(__name__)
        transfer_scene_id = (self.settings.wechat_transfer_scene_id or "").strip() or "1005"
        transfer_remark = (self.settings.wechat_transfer_remark or "").strip() or "分销佣金提现"
        user_recv_perception = (self.settings.wechat_transfer_user_recv_perception or "").strip() or "劳务报酬"
        payload = {
            "appid": self.settings.wechat_app_id,
            "out_bill_no": out_bill_no,
            "transfer_scene_id": transfer_scene_id,
            "openid": openid,
            "transfer_amount": int(amount),
            "transfer_remark": transfer_remark,
            "user_recv_perception": user_recv_perception,
        }
        if self.settings.wechat_transfer_notify_url or self.settings.wechat_notify_url:
            payload["notify_url"] = self.settings.wechat_transfer_notify_url or self.settings.wechat_notify_url
        report_infos = self._build_transfer_scene_report_infos()
        if report_infos:
            payload["transfer_scene_report_infos"] = report_infos
        body_text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        logger.info(
            "wechat.transfer.request out_bill_no=%s endpoint=%s mchid=%s appid=%s amount=%s has_openid=%s scene_id=%s",
            out_bill_no,
            self.TRANSFER_TO_BALANCE_URL,
            self.settings.wechat_mch_id,
            self.settings.wechat_app_id,
            payload["transfer_amount"],
            bool(openid),
            transfer_scene_id,
        )
        data = self._request_json(
            method="POST",
            url=self.TRANSFER_TO_BALANCE_URL,
            url_path="/v3/fund-app/mch-transfer/transfer-bills",
            body_text=body_text,
        )
        return TransferResult(
            out_bill_no=data.get("out_bill_no") or out_bill_no,
            transfer_bill_no=data.get("transfer_bill_no") or "",
            state=(data.get("state") or "ACCEPTED").upper(),
            package_info=data.get("package_info") or "",
            fail_reason=data.get("fail_reason") or "",
        )

    def query_transfer_bill(self, *, out_bill_no: str) -> TransferResult:
        logger = logging.getLogger(__name__)
        url_path = "/v3/fund-app/mch-transfer/transfer-bills/out-bill-no/{}".format(out_bill_no)
        authorization = self._build_authorization("GET", url_path, "")
        response = requests.get(
            self.QUERY_TRANSFER_BILL_URL.format(out_bill_no=out_bill_no),
            timeout=15,
            headers={
                "Authorization": authorization,
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        logger.info(
            "wechat.transfer.query out_bill_no=%s status_code=%s body=%s",
            out_bill_no,
            response.status_code,
            response.text[:1000],
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ValidationError(message=self._build_transfer_error_message(response)) from exc
        data = response.json()
        return TransferResult(
            out_bill_no=data.get("out_bill_no") or out_bill_no,
            transfer_bill_no=data.get("transfer_bill_no") or "",
            state=(data.get("state") or "").upper(),
            package_info=data.get("package_info") or "",
            fail_reason=data.get("fail_reason") or "",
        )

    def query_balance(self, *, account_type: str) -> BalanceResult:
        logger = logging.getLogger(__name__)
        normalized = (account_type or "").strip().upper() or "OPERATION"
        if normalized not in {"BASIC", "OPERATION", "FEES"}:
            raise ValidationError(message="unsupported balance account_type")
        url_path = "/v3/merchant/fund/balance/{}".format(normalized)
        url = self.BALANCE_URL_TEMPLATE.format(account_type=normalized)
        logger.info("wechat.balance.request account_type=%s endpoint=%s mchid=%s", normalized, url, self.settings.wechat_mch_id)
        data = self._request_json(method="GET", url=url, url_path=url_path)
        logger.info("wechat.balance.response account_type=%s data=%s", normalized, json.dumps(data, ensure_ascii=False)[:1000])
        return BalanceResult(
            account_type=normalized,
            available_amount=int(data.get("available_amount") or 0),
            pending_amount=int(data.get("pending_amount") or 0),
        )

    def _build_transfer_scene_report_infos(self) -> list[dict[str, str]]:
        primary = (self.settings.wechat_transfer_report_primary or "").strip()
        secondary = (self.settings.wechat_transfer_report_secondary or "").strip()
        scene_id = (self.settings.wechat_transfer_scene_id or "").strip() or "1005"
        if scene_id == "1005":
            return [
                {"info_type": "岗位类型", "info_content": primary or "校园分销"},
                {"info_type": "报酬说明", "info_content": secondary or "分销佣金提现"},
            ]
        if scene_id == "1000":
            return [
                {"info_type": "活动名称", "info_content": primary or "分销激励"},
                {"info_type": "奖励说明", "info_content": secondary or "分销佣金提现"},
            ]
        return []

    def _build_transfer_error_message(self, response) -> str:
        try:
            payload = response.json()
        except Exception:
            payload = {}
        code = str(payload.get("code") or "").strip()
        message = str(payload.get("message") or "").strip()
        if code or message:
            detail = " ".join(part for part in [code, message] if part).strip()
            return "wechat transfer failed: {}".format(detail)
        body = (response.text or "").strip()
        if body:
            return "wechat transfer failed: {}".format(body[:300])
        return "wechat transfer failed: http {}".format(response.status_code)

    def verify_callback_signature(self, headers: dict, body_text: str) -> None:
        if not self.platform_public_key:
            raise RuntimeError("missing WeChat platform certificate/public key")

        timestamp = headers.get("Wechatpay-Timestamp", "")
        nonce = headers.get("Wechatpay-Nonce", "")
        signature = headers.get("Wechatpay-Signature", "")
        serial = headers.get("Wechatpay-Serial", "")

        if not timestamp or not nonce or not signature:
            raise RuntimeError("missing WeChat callback signature headers")
        if self.settings.wechat_platform_serial_no and serial != self.settings.wechat_platform_serial_no:
            raise RuntimeError("unexpected WeChat platform serial")

        now_ts = int(time.time())
        if abs(now_ts - int(timestamp)) > self.settings.wechat_callback_tolerance:
            raise RuntimeError("WeChat callback timestamp expired")

        message = f"{timestamp}\n{nonce}\n{body_text}\n".encode("utf-8")
        self.platform_public_key.verify(
            base64.b64decode(signature),
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

    def decrypt_callback_resource(self, resource: dict) -> dict:
        if not self.settings.wechat_api_v3_key:
            raise RuntimeError("missing APIv3 key")

        nonce = resource.get("nonce")
        associated_data = resource.get("associated_data", "")
        ciphertext = resource.get("ciphertext")
        if not nonce or not ciphertext:
            raise RuntimeError("invalid callback resource")

        aesgcm = AESGCM(self.settings.wechat_api_v3_key.encode("utf-8"))
        plaintext = aesgcm.decrypt(
            nonce.encode("utf-8"),
            base64.b64decode(ciphertext),
            associated_data.encode("utf-8") if associated_data else None,
        )
        return json.loads(plaintext.decode("utf-8"))

    def parse_notification(self, payload: dict) -> PaymentNotification:
        logger = logging.getLogger(__name__)
        if payload.get("resource"):
            headers = payload.get("_headers") or {}
            body_text = payload.get("_raw_body") or json.dumps(
                {key: value for key, value in payload.items() if not key.startswith("_")},
                separators=(",", ":"),
                ensure_ascii=False,
            )
            logger.info("wechat.pay.notify.v3.received has_resource=true headers=%s", sorted(headers.keys()))
            self.verify_callback_signature(headers, body_text)
            transaction = self.decrypt_callback_resource(payload["resource"])
            amount_info = transaction.get("amount") or {}
            trade_state = (transaction.get("trade_state") or "").upper()
            logger.info(
                "wechat.pay.notify.v3.parsed out_trade_no=%s transaction_id=%s trade_state=%s payer_total=%s",
                transaction.get("out_trade_no"),
                transaction.get("transaction_id"),
                trade_state,
                amount_info.get("payer_total") or amount_info.get("total"),
            )
            return PaymentNotification(
                notify_id=payload.get("id") or transaction.get("transaction_id") or "notify-default",
                order_id=transaction["out_trade_no"],
                amount=int(amount_info.get("payer_total") or amount_info.get("total") or 0),
                status="success" if trade_state == "SUCCESS" else trade_state.lower() or "failed",
                paid_at=transaction.get("success_time") or datetime.utcnow().isoformat() + "Z",
            )

        logger.info(
            "wechat.pay.notify.mock.received order_id=%s notify_id=%s status=%s",
            payload.get("order_id"),
            payload.get("notify_id"),
            payload.get("status", "success"),
        )
        return PaymentNotification(
            notify_id=payload.get("notify_id", "notify-default"),
            order_id=payload["order_id"],
            amount=payload["amount"],
            status=payload.get("status", "success"),
            paid_at=payload.get("paid_at", datetime.utcnow().isoformat() + "Z"),
        )


class NullWechatPayClient(WechatPayClient):
    def create_prepay(self, *, order_id: str, amount: int, openid: str) -> PaymentParams:
        return PaymentParams(
            timeStamp="1713600000",
            nonceStr="nonce-not-configured",
            package="prepay_id={}".format(order_id),
            signType="RSA",
            paySign="not-configured",
            prepay_id=order_id,
        )

    def parse_notification(self, payload: dict) -> PaymentNotification:
        return PaymentNotification(
            notify_id=payload.get("notify_id", "notify-default"),
            order_id=payload["order_id"],
            amount=payload["amount"],
            status=payload.get("status", "success"),
            paid_at=payload.get("paid_at", datetime.utcnow().isoformat() + "Z"),
        )

    def transfer_to_balance(self, *, out_bill_no: str, amount: int, openid: str, user_name: str = "") -> TransferResult:
        return TransferResult(
            out_bill_no=out_bill_no,
            transfer_bill_no="mock-transfer-{}".format(out_bill_no),
            state="SUCCESS",
            package_info="mock",
        )

    def query_transfer_bill(self, *, out_bill_no: str) -> TransferResult:
        return TransferResult(
            out_bill_no=out_bill_no,
            transfer_bill_no="mock-transfer-{}".format(out_bill_no),
            state="SUCCESS",
            package_info="mock",
        )

    def query_balance(self, *, account_type: str) -> BalanceResult:
        normalized = (account_type or "").strip().upper() or "OPERATION"
        return BalanceResult(
            account_type=normalized,
            available_amount=0,
            pending_amount=0,
        )
