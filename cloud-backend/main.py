from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Sentry Error Monitoring
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.getenv("ENV", "production"),
        integrations=[FastApiIntegration(transaction_style="url")],
        traces_sample_rate=0.1,
        default_integrations=False,  # Disable default integrations to avoid langchain issues
        auto_enabling_integrations=False,  # Disable auto-enabling integrations
    )

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 K24 Cloud Backend starting...")
    
    yield
    
    # Shutdown
    logger.info("🛑 K24 Cloud Backend shutting down...")

# Create FastAPI app
app = FastAPI(
    title="K24 Cloud API",
    description="Cloud-hosted API for K24 multi-tenant platform",
    version="1.0.0",
    lifespan=lifespan
)

# Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if sentry_dsn:
        sentry_sdk.capture_exception(exc)
    
    logger.error(f"Global Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tauri.localhost",
        "k24://localhost",
        "https://api.k24.ai",
        "http://localhost:3000",
        "http://localhost:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include cloud routers
# NOTE: Some routers temporarily commented out until backend.* dependencies are refactored
from routers import whatsapp_cloud

# Include routers
# TODO: Uncomment these after extracting shared modules from backend/
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(devices.router, prefix="/api/devices", tags=["Devices"]) 
# app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["WhatsApp"])
app.include_router(whatsapp_cloud.router, prefix="/api/whatsapp/cloud", tags=["WhatsApp Cloud"])
# app.include_router(baileys.router, prefix="/api/baileys", tags=["Baileys"])
# app.include_router(query.router, prefix="/api/query", tags=["Smart Query"])

@app.get("/")
async def root():
    return {
        "name": "K24 Cloud API",
        "version": "1.0.0",
        "status": "running",
        "environment": os.getenv("ENV", "development")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "k24-cloud-backend"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development"
    )
