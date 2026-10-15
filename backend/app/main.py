"""
Main FastAPI application
Cloud Monitoring System - COMPLETE with ML Features
"""

from contextlib import asynccontextmanager
from app.services.prometheus import prometheus_client
from app.services.scheduler import start_scheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from app.config import settings
from app.database import init_db
from app.routers import auth, metrics, instances, health, ml_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks (replaces the deprecated @app.on_event API)."""
    logger.info("Starting Cloud Monitoring System - ML Enhanced v2.0.0")
    init_db()
    start_scheduler()
    logger.info("Database initialized successfully")

    yield

    logger.info("Shutting down Cloud Monitoring System")


# Create FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="Cloud Monitoring System - ML Enhanced",
    version="2.0.0",
    description=(
        "Production-grade cloud monitoring system with 10 ML features for AWS EC2 instances.\n\n"
        "## 🔐 How to Authenticate\n"
        "1. Click the **Authorize** button (🔒 icon) at the top right\n"
        "2. Enter your **username** and **password**\n"
        "3. Click **Authorize** → then **Close**\n"
        "4. All endpoints will now work!\n"
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
    },
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": False,
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include routers - ORIGINAL FEATURES
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(instances.router, prefix="/api")

# Include ML routes - ML FEATURES
app.include_router(ml_routes.router, prefix="/api")


# Remove 422 Validation Error from Swagger docs
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Remove 422 responses from all paths
    for path in openapi_schema.get("paths", {}).values():
        for method in path.values():
            responses = method.get("responses", {})
            responses.pop("422", None)
    # Remove ValidationError schema
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    schemas.pop("ValidationError", None)
    schemas.pop("HTTPValidationError", None)
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


@app.get("/")
async def root():
    """Root endpoint with feature list"""
    return {
        "message": "Cloud Monitoring System API - ML Enhanced",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/api/docs",
        "features": {
            "original": [
                "Real-time CPU/Memory/Disk/Network metrics",
                "Prometheus integration",
                "Alert system with email notifications",
                "Instance management",
                "JWT authentication",
                "Multi-user support"
            ],
            "ml_enhanced": [
                "Anomaly detection (Isolation Forest + One-Class SVM)",
                "CPU usage prediction (RandomForest forecasting)",
                "Memory usage forecasting (RandomForest + trend-based leak detection)",
                "Memory leak detection",
                "Instance health scoring (0-100)",
                "System failure prediction",
                "Root cause analysis",
                "Capacity planning (14-30 days)",
                "Auto-scaling recommendations",
                "ML dashboard summary"
            ]
        },
        "endpoints": {
            "health": "/api/health",
            "auth": "/api/auth (login, register)",
            "metrics": "/api/metrics (cpu, memory, disk, network)",
            "instances": "/api/instances (CRUD operations)",
            "ml": "/api/ml (10 ML features)",
            "docs": "/api/docs (Swagger UI)"
        }
    }


@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Cloud Monitoring System API",
        "version": "2.0.0",
        "documentation": "/api/docs",
        "redoc": "/api/redoc",
        "openapi_schema": "/api/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
