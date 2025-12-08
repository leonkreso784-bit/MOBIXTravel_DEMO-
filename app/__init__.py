"""MOBIX Travel FastAPI application package."""

import os
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .routers.chat import router as chat_router
from .routers.plan import router as plan_router
from .routers.places import router as places_router
from .routers.auth import router as auth_router
from .routers.community import router as community_router
from .routers.planner import router as planner_router
from .database import SessionLocal, engine
from . import models

# Create all database tables
models.Base.metadata.create_all(bind=engine)

# Load .env from project root (for local development only)
# On Railway/production, env vars are set directly in the environment
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    print(f"[MOBIX] Loading .env from: {env_path}")
    load_dotenv(dotenv_path=env_path, override=False)  # Don't override existing env vars
else:
    print(f"[MOBIX] No .env file found (using system environment variables)")

# Check API keys exist (don't log actual values!)
api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("PENAI_API_KEY", "")
if api_key:
    print("[MOBIX] ✅ OpenAI API Key configured")
else:
    print("[MOBIX] ⚠️ WARNING: No OpenAI API Key found!")

# Security: Define allowed origins (restrict in production)
ALLOWED_ORIGINS = [
    "https://mobix-travel-demo.vercel.app",
    "https://mobix-travel.vercel.app",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Use env var if set, otherwise use secure defaults
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
if cors_origins == [""]:
    cors_origins = ALLOWED_ORIGINS

app = FastAPI(
    title="MOBIX Travel API", 
    version="3.0",
    docs_url=None,  # Disable Swagger docs in production
    redoc_url=None,  # Disable ReDoc in production
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],  # Only needed methods
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)

# Security middleware for headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

@app.get("/api")
async def api_info():
    return {"status": "ok", "service": "MOBIX Travel"}

app.include_router(chat_router)
app.include_router(plan_router)
app.include_router(places_router)
app.include_router(auth_router)
app.include_router(community_router)
app.include_router(planner_router)

# Database dependency
def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()

from fastapi.responses import FileResponse

# Mount uploads directory BEFORE UI mount (order matters!)
if os.path.isdir("public/uploads"):
	app.mount("/uploads", StaticFiles(directory="public/uploads"), name="uploads")
	print("[MOBIX] Mounted /uploads directory for profile images")

# Mount UI directory (prioritize ui-chat)
if os.path.isdir("ui-chat"):
	app.mount("/", StaticFiles(directory="ui-chat", html=True), name="ui")
	print("[MOBIX] Mounted /ui-chat directory")
elif os.path.isdir("ui-new"):
	app.mount("/", StaticFiles(directory="ui-new", html=True), name="ui")
	print("[MOBIX] Mounted /ui-new directory")
elif os.path.isdir("ui"):
	app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
	print("[MOBIX] Mounted /ui directory (fallback)")


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon to prevent 404 errors."""
    favicon_path = Path(__file__).parent.parent / "ui" / "assets" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    # Return empty response if no favicon
    return FileResponse(Path(__file__).parent.parent / "ui" / "assets" / "favicon.ico", status_code=204)


__all__ = ["app"]
