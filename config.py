from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    node_api_token: str
    model_base_url: str
    model_api_key: str
    model_name: str
    database_path: Path
    profile_path: Path
    model_timeout_seconds: float
    max_history_messages: int


def load_settings() -> Settings:
    token = os.getenv("NODE_API_TOKEN", "").strip()
    if not token or token == "replace-with-a-long-random-token":
        raise RuntimeError("Set NODE_API_TOKEN to a long random value before starting the service.")

    base_url = os.getenv("MODEL_BASE_URL", "").strip().rstrip("/")
    model_name = os.getenv("MODEL_NAME", "").strip()
    if not base_url or not model_name:
        raise RuntimeError("Set MODEL_BASE_URL and MODEL_NAME to an OpenAI-compatible chat completions endpoint.")

    return Settings(
        node_api_token=token,
        model_base_url=base_url,
        model_api_key=os.getenv("MODEL_API_KEY", "").strip(),
        model_name=model_name,
        database_path=Path(os.getenv("DATABASE_PATH", "./data/agent.sqlite3")),
        profile_path=Path(os.getenv("AGENT_PROFILE_PATH", "./data/agent_profile.md")),
        model_timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "120")),
        max_history_messages=max(0, int(os.getenv("MAX_HISTORY_MESSAGES", "24"))),
    )
