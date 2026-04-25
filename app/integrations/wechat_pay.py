import base64
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import padding


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


class WechatPayClient:
    def create_prepay(self, *, order_id: str, amount: int, openid: str) -> PaymentParams:
        raise NotImplementedError

    def parse_notification(self, payload: dict) -> PaymentNotification:
        raise NotImplementedError


class RealWechatPayClient(WechatPayClient):
    PAY_JSAPI_URL = "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi"

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
        authorization = self._build_authorization("POST", "/v3/pay/transactions/jsapi", body_text)
        response = requests.post(
            self.PAY_JSAPI_URL,
            data=body_text.encode("utf-8"),
            timeout=15,
            headers={
                "Authorization": authorization,
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        response.raise_for_status()
        data = response.json()
        prepay_id = data["prepay_id"]
        payment_params = self._build_pay_sign(prepay_id)
        return PaymentParams(
            timeStamp=payment_params["timeStamp"],
            nonceStr=payment_params["nonceStr"],
            package=payment_params["package"],
            signType=payment_params["signType"],
            paySign=payment_params["paySign"],
            prepay_id=prepay_id,
        )

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
        if payload.get("resource"):
            headers = payload.get("_headers") or {}
            body_text = payload.get("_raw_body") or json.dumps(
                {key: value for key, value in payload.items() if not key.startswith("_")},
                separators=(",", ":"),
                ensure_ascii=False,
            )
            self.verify_callback_signature(headers, body_text)
            transaction = self.decrypt_callback_resource(payload["resource"])
            amount_info = transaction.get("amount") or {}
            trade_state = (transaction.get("trade_state") or "").upper()
            return PaymentNotification(
                notify_id=payload.get("id") or transaction.get("transaction_id") or "notify-default",
                order_id=transaction["out_trade_no"],
                amount=int(amount_info.get("payer_total") or amount_info.get("total") or 0),
                status="success" if trade_state == "SUCCESS" else trade_state.lower() or "failed",
                paid_at=transaction.get("success_time") or datetime.utcnow().isoformat() + "Z",
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
