import hashlib
import hmac
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

TOKEN_REGISTRY_PATH = Path("server/auth/token_registry.json")

_token_db = None


def load_token_registry() -> dict:
    global _token_db
    if _token_db is None:
        with open(TOKEN_REGISTRY_PATH) as f:
            _token_db = json.load(f)
    return _token_db


def verify_token(token: str) -> Optional[str]:
    """
    토큰이 유효하고 만료되지 않았으면 user_id 반환,
    아니면 None 반환
    """
    token_db = load_token_registry()
    entry = token_db.get(token)
    if not entry:
        return None

    expires_at = datetime.fromisoformat(entry["expires_at"].replace("Z", "+00:00"))
    now = datetime.utcnow()

    if now > expires_at:
        print("[AUTH] Token expired.")
        return None

    return entry["user_id"]


def get_secret_for_token(token: str) -> Optional[str]:
    """
    토큰에 대응하는 HMAC secret 반환
    """
    token_db = load_token_registry()
    entry = token_db.get(token)
    if entry:
        return entry["secret"]
    return None


def verify_hmac_signature(token: str, payload: str, signature: str) -> bool:
    """
    주어진 payload와 secret을 이용해 HMAC을 계산하고,
    받은 signature와 비교해서 일치 여부 반환
    """
    secret = get_secret_for_token(token)
    if not secret:
        return False

    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
