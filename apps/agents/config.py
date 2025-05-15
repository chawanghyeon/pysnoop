# apps/common/config.py
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    agent_host: str = "localhost"
    agent_port: int = 8888
    agent_user_id: str  # 필수: .env 또는 환경변수에 설정 필요
    agent_token: str  # 필수
    agent_secret: str  # 필수
    agent_interval: int = 10
    server_cert_path: Optional[str] = None  # 문자열로 받고, 사용할 때 Path 객체로 변환
    agent_allow_insecure_ssl: bool = False
