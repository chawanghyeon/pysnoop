# apps/server/auth/session.py
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional  # Added Dict, Any

# Determine path to token_registry.json robustly
_CURRENT_DIR = Path(__file__).resolve().parent
TOKEN_REGISTRY_PATH = _CURRENT_DIR / "token_registry.json"

# Mypy fix: Add type annotation for global variable
_token_db: Optional[Dict[str, Any]] = None
_token_db_loaded_successfully: bool = False  # Type annotation for bool


def load_token_registry() -> Dict[str, Any]:  # Return type is Dict, not Optional here
    global _token_db, _token_db_loaded_successfully
    if _token_db is None:  # Load only once
        if not TOKEN_REGISTRY_PATH.exists():
            # Flake8 fix: Shorten line
            print(f"[ERROR][AUTH] Token registry file not found: " f"{TOKEN_REGISTRY_PATH}")
            _token_db = {}
            _token_db_loaded_successfully = False
            return _token_db  # Return the empty dict
        try:
            with open(TOKEN_REGISTRY_PATH, "r", encoding="utf-8") as f:
                _token_db = json.load(f)
            _token_db_loaded_successfully = True
            # Flake8 fix: Shorten line
            print(
                f"[INFO][AUTH] Token registry loaded successfully " f"from {TOKEN_REGISTRY_PATH}."
            )
        except json.JSONDecodeError as e:
            # Flake8 fix: Shorten line
            print(
                f"[ERROR][AUTH] Failed to decode token registry JSON "
                f"from {TOKEN_REGISTRY_PATH}: {e}"
            )
            _token_db = {}
            _token_db_loaded_successfully = False
        except Exception as e:
            # Flake8 fix: Shorten line
            print(
                f"[ERROR][AUTH] Failed to load token registry " f"from {TOKEN_REGISTRY_PATH}: {e}"
            )
            _token_db = {}
            _token_db_loaded_successfully = False
    # Ensure _token_db is not None before returning, even if loading failed
    return _token_db if _token_db is not None else {}


def verify_token(token: str) -> Optional[str]:
    """
    Validates a token. Returns user_id if valid and not expired, otherwise None.
    """
    token_db = load_token_registry()
    if not _token_db_loaded_successfully and not token_db:
        # Flake8 fix: Shorten line
        print(
            "[WARN][AUTH] Token verification attempted but token "
            "registry failed to load or is empty."
        )
        return None

    entry = token_db.get(token)
    if not entry:
        return None

    try:
        user_id = entry.get("user_id")
        expires_at_str = entry.get("expires_at")

        if not user_id or not expires_at_str:
            # Flake8 fix: Shorten line
            print(
                f"[WARN][AUTH] Token entry for {token[:6]}... " "is missing user_id or expires_at."
            )
            return None

        if expires_at_str.endswith("Z"):
            expires_at = datetime.fromisoformat(expires_at_str[:-1] + "+00:00")
        else:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except ValueError:
                print(
                    f"[WARN][AUTH] Invalid ISO format for expires_at: "
                    f"'{expires_at_str}' for token {token[:6]}..."
                )
                return None

        now = datetime.now(timezone.utc)

        if now > expires_at:
            print(
                f"[INFO][AUTH] Token expired for user '{user_id}'. "
                f"Expires: {expires_at}, Now: {now}"
            )
            return None

        issued_at_str = entry.get("issued_at")
        if issued_at_str:
            try:
                if issued_at_str.endswith("Z"):
                    issued_at = datetime.fromisoformat(issued_at_str[:-1] + "+00:00")
                else:
                    issued_at = datetime.fromisoformat(issued_at_str)
                    if issued_at.tzinfo is None:
                        issued_at = issued_at.replace(tzinfo=timezone.utc)
                if now < issued_at:
                    print(
                        f"[INFO][AUTH] Token for user '{user_id}' not yet "
                        f"valid (issued_at: {issued_at})."
                    )
                    return None
            except ValueError:
                # Flake8 fix: Shorten line
                print(
                    f"[WARN][AUTH] Invalid ISO format for issued_at: "
                    f"'{issued_at_str}' for token {token[:6]}..."
                )

        return user_id
    except KeyError as e:
        print(f"[WARN][AUTH] Token data for {token[:6]}... " f"missing required field: {e}")
        return None
    except ValueError as e:
        print(
            f"[WARN][AUTH] Invalid date format in token registry " f"for token {token[:6]}... : {e}"
        )
        return None


def get_secret_for_token(token: str) -> Optional[str]:
    """
    Retrieves the HMAC secret for a given token.
    """
    token_db = load_token_registry()
    entry = token_db.get(token)
    if entry:
        secret = entry.get("secret")
        if not secret:
            print(f"[WARN][AUTH] Secret not found in token entry for {token[:6]}...")
        return secret
    return None


def verify_hmac_signature(token: str, payload_str: str, signature_from_client: str) -> bool:
    """
    Verifies the HMAC signature of a payload.
    """
    secret = get_secret_for_token(token)
    if not secret:
        # Flake8 fix: Shorten line
        print(
            f"[WARN][AUTH] HMAC verification failed: No secret found " f"for token {token[:6]}..."
        )
        return False

    try:
        expected_signature = hmac.new(
            secret.encode(), payload_str.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature_from_client)
    except Exception as e:
        print(f"[ERROR][AUTH] Exception during HMAC signature verification: {e}")
        return False
