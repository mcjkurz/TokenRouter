"""Main FastAPI application."""
import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.providers import provider_config
from app.api import proxy, admin, registration

logger = logging.getLogger("uvicorn.error")

settings.validate_required_settings()

app = FastAPI(
    title="TokenRouter",
    description="Lightweight proxy service for sharing LLM accounts with token quotas",
    version="1.0.0",
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None
)

app.include_router(proxy.router, tags=["proxy"])
app.include_router(admin.router, tags=["admin"], include_in_schema=False)
app.include_router(registration.router, tags=["registration"])

admin_ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_ui")
if os.path.exists(admin_ui_path):
    app.mount("/static", StaticFiles(directory=admin_ui_path), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    logger.info("✅ TokenRouter started successfully!")
    logger.info("📍 Proxy endpoint: /v1/chat/completions")
    logger.info("🔧 Admin interface: /admin")
    logger.info("👤 Registration page: /register")
    
    logger.info(f"🔌 Providers configured: {', '.join(provider_config.providers.keys())}")
    if provider_config.default_provider:
        logger.info(f"📦 Default provider: {provider_config.default_provider_name}")


@app.get("/")
async def root():
    """Root endpoint - minimal response."""
    return {"status": "ok"}


@app.get("/admin")
async def admin_ui():
    """Serve admin UI."""
    admin_html = os.path.join(admin_ui_path, "index.html")
    if os.path.exists(admin_html):
        return FileResponse(admin_html)
    return {
        "message": "Admin UI not found",
        "api_docs": "/docs"
    }


@app.get("/register")
async def register_page():
    """Serve registration UI."""
    register_html = os.path.join(admin_ui_path, "register.html")
    if os.path.exists(register_html):
        return FileResponse(register_html)
    return {
        "message": "Registration UI not found",
        "api_endpoint": "/register"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from sqlalchemy import text
    from app.core.database import SessionLocal
    
    status_response = {"status": "healthy", "components": {}}
    
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        status_response["components"]["database"] = "ok"
    except Exception as e:
        status_response["status"] = "unhealthy"
        status_response["components"]["database"] = f"error: {str(e)}"
    
    if provider_config.providers:
        status_response["components"]["providers"] = {
            "count": len(provider_config.providers),
            "names": list(provider_config.providers.keys()),
            "default": provider_config.default_provider_name
        }
    else:
        status_response["status"] = "unhealthy"
        status_response["components"]["providers"] = "no providers configured"
    
    return status_response


@app.post("/admin/reload-providers")
async def reload_providers():
    """Reload provider configuration from providers.json without restart."""
    from app.core.auth import get_admin_auth
    from fastapi import Depends
    
    try:
        provider_config.reload()
        return {
            "status": "ok",
            "providers": list(provider_config.providers.keys()),
            "default": provider_config.default_provider_name
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e)
        }
