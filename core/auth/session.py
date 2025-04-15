# core/auth/session.py
import hmac
import hashlib
import base64
import time

SECRET_KEY = b"supersecret"  # 보안적으로는 환경변수에서 받아야 함


def generate_token(user_id: str, expire_seconds: int = 3600) -> str:
    exp = int(time.time()) + expire_seconds
    payload = f"{user_id}:{exp}"
    sig = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).digest()
    token = f"{payload}:{base64.urlsafe_b64encode(sig).decode()}"
    return token


def verify_token(token: str) -> str | None:
    try:
        payload, sig_b64 = token.rsplit(":", 1)
        user_id, exp_str = payload.split(":")
        exp = int(exp_str)
        if time.time() > exp:
            return None  # 만료

        expected_sig = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).digest()
        if hmac.compare_digest(
            base64.urlsafe_b64encode(expected_sig).decode(), sig_b64
        ):
            return user_id
    except Exception:
        return None
    return None
