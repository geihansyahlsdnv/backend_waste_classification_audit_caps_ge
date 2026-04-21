from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from .core.config import settings
from .middleware.logging import logging_middleware

app = FastAPI(
    title="Waste Classification API",
    description="Backend API for waste classification using YOLOv8. Supports image classification, statistics tracking, and pricing management with JWT-based role access control.",
    version="1.0.0",
    contact={
        "name": "Development Team",
        "email": "developer@example.com"
    },
    openapi_tags=[
        {"name": "Authentication", "description": "User login and registration"},
        {"name": "Classification", "description": "Image classification endpoints"},
        {"name": "Statistics", "description": "Statistics and history endpoints"}
    ]
)

app.middleware("http")(logging_middleware)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    from datetime import datetime
    from .services.inference import inference_service
    from .services.redis_service import redis_service
    from .db.session import AsyncSessionLocal
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    try:
        model_info = inference_service.get_model_info()
        health["components"]["model"] = {"status": "healthy", "info": model_info}
    except Exception as e:
        health["components"]["model"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        health["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    try:
        await redis_service.set("health_check", "ok", 5)
        health["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    return JSONResponse(health)
from .api.endpoints import auth, classification, stats

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(classification.router, prefix="/api", tags=["Classification"])
app.include_router(stats.router, prefix="/api", tags=["Statistics"])

# Context Manager for Startup/Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("FastAPI is starting up...")
    
    # 1. Initialize database tables
    from .db.session import async_engine, Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Initialize MinIO client and download model weights
    from .services.minio_client import minio_client
    
    # 3. Load YOLOv8 model
    from .services.inference import inference_service
    await inference_service.load_model()
    
    print("Startup complete.")
    yield
    # --- SHUTDOWN ---
    print("FastAPI is shutting down...")
    await async_engine.dispose()  # Close engine connections
    print("Shutdown complete.")