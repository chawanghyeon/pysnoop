import argparse
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

TOKEN_PATH = Path("server/auth/token_registry.json")


def load_registry() -> dict:
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH) as f:
            return json.load(f)
    return {}


def save_registry(registry: dict):
    with open(TOKEN_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def issue_token(user_id: str, valid_days: int = 365):
    registry = load_registry()

    token = secrets.token_hex(16)
    secret = secrets.token_hex(32)
    issued_at = datetime.utcnow()
    expires_at = issued_at + timedelta(days=valid_days)

    registry[token] = {
        "user_id": user_id,
        "secret": secret,
        "issued_at": issued_at.isoformat() + "Z",
        "expires_at": expires_at.isoformat() + "Z",
    }

    save_registry(registry)

    print(f"✅ Token issued for {user_id}")
    print(f"TOKEN:  {token}")
    print(f"SECRET: {secret}")
    print(f"EXPIRES: {expires_at.isoformat()}Z")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Token manager for agents")
    parser.add_argument("user_id", help="Agent user ID")
    parser.add_argument("--days", type=int, default=365, help="Token validity (days)")

    args = parser.parse_args()
    issue_token(args.user_id, args.days)
