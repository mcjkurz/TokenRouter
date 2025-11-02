"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import os

from app.core.config import settings
from app.core.database import init_db
from app.api import proxy, admin

# Initialize configuration and validate required settings
settings.validate_required_settings()

# Create FastAPI app
app = FastAPI(
    title="TokenRouter",
    description="Lightweight proxy service for sharing LLM accounts with token quotas",
    version="1.0.0"
)

# Include routers
app.include_router(proxy.router, tags=["proxy"])
app.include_router(admin.router, tags=["admin"])

# Mount static files for admin UI
admin_ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_ui")
if os.path.exists(admin_ui_path):
    app.mount("/static", StaticFiles(directory=admin_ui_path), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    print("\n✅ TokenRouter started successfully!")
    print(f"📍 Proxy endpoint: http://{settings.host}:{settings.port}/v1/chat/completions")
    print(f"🔧 Admin interface: http://{settings.host}:{settings.port}/admin")
    print(f"📖 API docs: http://{settings.host}:{settings.port}/docs\n")


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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from sqlalchemy import text
    from app.core.database import SessionLocal
    
    status = {"status": "healthy", "components": {}}
    
    # Check database
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        status["components"]["database"] = "ok"
    except Exception as e:
        status["status"] = "unhealthy"
        status["components"]["database"] = f"error: {str(e)}"
    
    # Check provider config
    if settings.provider_api_key:
        status["components"]["provider_config"] = "ok"
    else:
        status["components"]["provider_config"] = "missing_api_key"
    
    return status

