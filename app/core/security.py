import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_text(plaintext: str, key: str) -> str:
    key_bytes = key.encode("utf-8")[:32].ljust(32, b"0")
    nonce = os.urandom(12)
    cipher = AESGCM(key_bytes)
    ciphertext = cipher.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_text(ciphertext: str, key: str) -> str:
    key_bytes = key.encode("utf-8")[:32].ljust(32, b"0")
    payload = base64.b64decode(ciphertext.encode("utf-8"))
    nonce = payload[:12]
    encrypted = payload[12:]
    cipher = AESGCM(key_bytes)
    plaintext = cipher.decrypt(nonce, encrypted, None)
    return plaintext.decode("utf-8")


def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return phone
    return "{}****{}".format(phone[:3], phone[-4:])

