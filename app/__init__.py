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

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
print(f"[MOBIX] Looking for .env at: {env_path}")
print(f"[MOBIX] .env exists: {env_path.exists()}")
load_dotenv(dotenv_path=env_path, override=True)

# Debug: Print first 20 chars of API key on startup
api_key = os.getenv("OPENAI_API_KEY", "")
if api_key:
    print(f"[MOBIX] OpenAI API Key loaded: {api_key[:20]}...")
else:
    print("[MOBIX] WARNING: No OpenAI API Key found!")

app = FastAPI(title="MOBIX Travel API", version="3.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
	allow_methods=["*"],
	allow_headers=["*"],
	allow_credentials=True,
)

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


@app.get("/api")
async def api_info():
	return {"status": "ok", "service": "MOBIX Travel"}


@app.get("/api/debug/env")
async def debug_env():
	"""Debug endpoint to check environment variables."""
	api_key = os.getenv("OPENAI_API_KEY", "")
	return {
		"api_key_exists": bool(api_key),
		"api_key_first_20": api_key[:20] if api_key else "N/A",
		"api_key_length": len(api_key) if api_key else 0,
		"env_path": str(Path(__file__).parent.parent / ".env"),
	}


__all__ = ["app"]
