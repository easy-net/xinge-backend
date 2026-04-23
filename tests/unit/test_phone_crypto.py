from app.core.security import decrypt_text, encrypt_text, mask_phone


def test_encrypt_and_decrypt_phone():
    key = "0123456789abcdef0123456789abcdef"
    ciphertext = encrypt_text("13800138000", key)
    assert decrypt_text(ciphertext, key) == "13800138000"


def test_mask_phone():
    assert mask_phone("13800138000") == "138****8000"

