import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hashlib import sha256

def _key_from_base64(s: str) -> bytes:
    key = base64.b64decode(s)
    if len(key) != 32:
        raise ValueError("PROFILES_CRYPTO_KEY_BASE64 must decode to 32 bytes")
    return key

class CryptoBox:
    def __init__(self, key_base64: str):
        self._key = _key_from_base64(key_base64)

    def encrypt(self, plaintext: bytes) -> bytes:
        aes = AESGCM(self._key)
        nonce = os.urandom(12)
        ct = aes.encrypt(nonce, plaintext, None)
        return nonce + ct

    def decrypt(self, blob: bytes) -> bytes:
        aes = AESGCM(self._key)
        nonce, ct = blob[:12], blob[12:]
        return aes.decrypt(nonce, ct, None)

def normalize_e164(phone_raw: str) -> str:
    import phonenumbers
    parsed = phonenumbers.parse(phone_raw, None)
    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        raise ValueError("Invalid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

def phone_hash(e164: str, pepper: str) -> bytes:
    h = sha256()
    h.update(pepper.encode("utf-8"))
    h.update(e164.encode("utf-8"))
    return h.digest()
