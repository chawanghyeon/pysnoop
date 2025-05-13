import argparse
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

# 스크립트 파일의 디렉토리를 기준으로 token_registry.json 경로 설정
_CURRENT_DIR = Path(__file__).resolve().parent
TOKEN_PATH = _CURRENT_DIR / "token_registry.json"


def load_registry() -> dict:
    if TOKEN_PATH.exists():
        # 파일이 존재하면 읽어서 반환
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:  # utf-8 인코딩 명시
            return json.load(f)
    return {}  # 파일 없으면 빈 딕셔너리 반환


def save_registry(registry: dict):
    # TOKEN_PATH의 부모 디렉토리가 존재하지 않으면 생성
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:  # utf-8 인코딩 명시
        json.dump(registry, f, indent=2, ensure_ascii=False)


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
