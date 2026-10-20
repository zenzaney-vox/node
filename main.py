from contextlib import asynccontextmanager
import logging
import secrets
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .config import load_settings
from .provider import ModelProviderError, generate_reply
from .storage import append_turn, create_session, has_session, initialize, load_messages, load_session


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = load_settings()
bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize(settings.database_path)
    if not settings.profile_path.is_file():
        raise RuntimeError(f"Agent profile file does not exist: {settings.profile_path}")
    yield


app = FastAPI(
    title="Ubuntu Agent Node",
    description=(
        "A local agent service for an external workflow or platform integration. "
        "Requires Bearer authentication for agent and session endpoints."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


class RunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    session_id: UUID | None = None


class RunResponse(BaseModel):
    session_id: UUID
    reply: str


async def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not secrets.compare_digest(credentials.credentials, settings.node_api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ubuntu-agent-node"}


@app.post("/v1/agent/run", response_model=RunResponse, tags=["agent"])
async def run_agent(request: RunRequest, _: None = Depends(require_token)) -> RunResponse:
    session_id = str(request.session_id or uuid4())
    if request.session_id is None:
        create_session(settings.database_path, session_id)
    elif not has_session(settings.database_path, session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        system_prompt = settings.profile_path.read_text(encoding="utf-8")
        history = load_messages(
            settings.database_path,
            session_id,
            limit=settings.max_history_messages,
        )
        reply = await generate_reply(settings, system_prompt, history, request.message)
    except ModelProviderError as error:
        logger.warning("Agent run failed: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except OSError as error:
        logger.exception("Could not read the agent profile")
        raise HTTPException(status_code=500, detail="Agent profile is unavailable") from error

    append_turn(settings.database_path, session_id, request.message, reply)
    return RunResponse(session_id=UUID(session_id), reply=reply)


@app.get("/v1/agent/sessions/{session_id}", tags=["agent"])
async def get_session(session_id: UUID, _: None = Depends(require_token)) -> dict:
    session = load_session(settings.database_path, str(session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
