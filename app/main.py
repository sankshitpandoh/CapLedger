from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.employees import router as employees_router
from app.api.routes.grants import router as grants_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import configure_logging
from app.core.session import SignedSessionMiddleware

settings = get_settings()
configure_logging(settings.debug)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment.lower() == "production" and settings.session_secret_key == "change-this-secret":
        raise RuntimeError("SESSION_SECRET_KEY must be set in production")
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SignedSessionMiddleware,
    secret_key=settings.session_secret_key,
    same_site="lax",
    https_only=settings.session_cookie_secure,
    max_age=60 * 60 * 12,
)

app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(grants_router)
app.include_router(dashboard_router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
