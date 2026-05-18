from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy import text
from .core.config import settings
from .middleware.logging import logging_middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("FastAPI is starting up...")
    
    # IMPORT BASE DAN ENGINE
    from .db.session import engine, Base
    # IMPORT MODELS 
    from .db import models 
    
    async with engine.begin() as conn:
        print("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)

    from .services.inference import inference_service
    await inference_service.load_model()
    
    print("Startup complete.")
    yield
    
    print("FastAPI is shutting down...")
    await engine.dispose() 
    print("Shutdown complete.")

app = FastAPI(
    title="Waste Classification API",
    description="Backend API for waste classification using YOLOv8.",
    version="1.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Authentication", "description": "User login and registration"},
        {"name": "Classification", "description": "Image classification endpoints"},
        {"name": "Statistics", "description": "Analytics and rich history"}
    ]
)

# Middleware
app.middleware("http")(logging_middleware)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# --- REVISI CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React default
        "http://127.0.0.1:3000",   # Loopback IP
        "http://localhost:5173",   # Vite default
        "http://localhost:8000",   # Docs testing
        "https://hargai.site",
        "https://app.hargai.site",
        "http://app.hargai.site",     # Production domain
        "http://hargai.site",      # Production domain (http fallback)
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import router
from .api.endpoints import auth, classification, stats, history, admin, pricing
import os

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Routing
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(classification.router, prefix="", tags=["Classification"])
app.include_router(stats.router, prefix="", tags=["Statistics"])
app.include_router(history.router, prefix="", tags=["History"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(pricing.router, prefix="", tags=["Pricing"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to HARG-AI Waste Classification API",
        "status": "online",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    from datetime import datetime
    from .db.session import AsyncSessionLocal
    
    health = {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "components": {}}
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    return JSONResponse(health)