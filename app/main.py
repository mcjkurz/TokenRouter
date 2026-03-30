"""Main FastAPI application."""
import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.providers import provider_config
from app.api import proxy, admin, registration
from app.services.proxy import proxy_service

logger = logging.getLogger("uvicorn.error")

settings.validate_required_settings()

app = FastAPI(
    title="TokenRouter",
    description="Lightweight proxy for sharing LLM accounts with token quotas",
    version="1.0.0",
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
)

app.include_router(proxy.router, tags=["proxy"])
app.include_router(admin.router, tags=["admin"], include_in_schema=False)
app.include_router(registration.router, tags=["registration"])

admin_ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_ui")
if os.path.exists(admin_ui_path):
    app.mount("/static", StaticFiles(directory=admin_ui_path), name="static")


@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("TokenRouter started")
    providers = ", ".join(provider_config.providers.keys())
    logger.info(f"Providers: {providers} (default: {provider_config.default_provider_name})")


@app.on_event("shutdown")
async def shutdown_event():
    await proxy_service.close()
    logger.info("TokenRouter stopped")


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/admin")
async def admin_ui():
    admin_html = os.path.join(admin_ui_path, "index.html")
    if os.path.exists(admin_html):
        return FileResponse(admin_html)
    return {"message": "Admin UI not found"}


@app.get("/register")
async def register_page():
    register_html = os.path.join(admin_ui_path, "register.html")
    if os.path.exists(register_html):
        return FileResponse(register_html)
    return {"message": "Registration UI not found"}


@app.get("/health")
async def health_check():
    from sqlalchemy import text
    from app.core.database import SessionLocal

    result = {"status": "healthy", "components": {}}

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        result["components"]["database"] = "ok"
    except Exception as e:
        result["status"] = "unhealthy"
        result["components"]["database"] = str(e)

    result["components"]["providers"] = list(provider_config.providers.keys())
    return result
