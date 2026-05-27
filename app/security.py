import hashlib
import hmac
import os
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request
from .settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
N_HEX = "894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7"
G = 7


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    return bool(password_hash) and pwd_context.verify(password, password_hash)


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = os.urandom(24).hex()
        request.session["csrf"] = token
    return token


def verify_csrf(request: Request, token: str | None) -> bool:
    return bool(token) and hmac.compare_digest(token, request.session.get("csrf", ""))


def serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().app_secret_key, salt="wow-gm-webpanel")


def sign_value(value: str) -> str:
    return serializer().dumps(value)


def unsign_value(value: str, max_age: int = 3600) -> str | None:
    try:
        return serializer().loads(value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def azeroth_sha_pass_hash(username: str, password: str) -> str:
    raw = f"{username.upper()}:{password.upper()}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest().upper()


def _le_bytes_to_int(data: bytes) -> int:
    return int.from_bytes(data, "little")


def _int_to_le_bytes(value: int, length: int = 32) -> bytes:
    return value.to_bytes(length, "little")


def azeroth_srp6_verifier(username: str, password: str, salt: bytes) -> bytes:
    h1 = hashlib.sha1(f"{username.upper()}:{password.upper()}".encode("utf-8")).digest()
    h2 = hashlib.sha1(salt + h1).digest()
    x = _le_bytes_to_int(h2)
    verifier = pow(G, x, int(N_HEX, 16))
    return _int_to_le_bytes(verifier, 32)


def verify_azeroth_password(username: str, password: str, row: dict) -> bool:
    if row.get("salt") is not None and row.get("verifier") is not None:
        salt = row["salt"]
        verifier = row["verifier"]
        if isinstance(salt, str):
            salt = bytes.fromhex(salt)
        if isinstance(verifier, str):
            verifier = bytes.fromhex(verifier)
        return hmac.compare_digest(azeroth_srp6_verifier(username, password, salt), verifier)
    if row.get("sha_pass_hash"):
        return hmac.compare_digest(azeroth_sha_pass_hash(username, password), str(row["sha_pass_hash"]).upper())
    return False
