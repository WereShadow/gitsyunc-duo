from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.models.database import init_db
from app.services.scheduler import scheduler
from app.api.routes import api_router

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gitsync_duo")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing GitSync Duo Database...")
    await init_db()
    
    # Optional seed demo data for developer testing
    try:
        from app.services.seed_service import seed_demo_data
        await seed_demo_data()
    except Exception as e:
        logger.warning(f"Demo seeder notice: {e}")

    logger.info("Starting background scheduler...")
    scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Stopping background scheduler...")
    scheduler.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="GitSync Duo - Two-person daily accountability platform driven by GitHub verification",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API
app.include_router(api_router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
