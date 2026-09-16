"""FlyCast FastAPI Main Application."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.brain.loader import is_brain_ready, get_brain
from app.jobs.cleanup import cleanup_expired_experiments
from app.demos.generate import ensure_demo_files
from app.api.brain import router as brain_router
from app.api.demos import router as demos_router
from app.api.experiments import router as experiments_router

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("flycast.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup checks and maintenance."""
    logger.info("FlyCast API backend booting...")

    # Purge expired experiments
    removed = cleanup_expired_experiments(ttl_hours=settings.EXPERIMENT_TTL_HOURS)
    if removed > 0:
        logger.info("Purged %d expired experiment directories", removed)

    # Ensure demo datasets are ready
    demo_dir = Path(settings.DATA_DIR) / "demos"
    ensure_demo_files(demo_dir)

    # Check brain readiness
    if is_brain_ready():
        try:
            brain = get_brain()
            logger.info(
                "MaleCNS connectome ready: %d neurons, %d edges",
                brain.num_neurons,
                brain.num_edges,
            )
        except Exception as e:
            logger.warning("Brain files exist but loading encountered error: %s", e)
    else:
        logger.warning("Connectome not yet ready at %s. Health endpoint will report initializing.", settings.brain_dir)

    yield

    logger.info("FlyCast API shutting down.")


app = FastAPI(
    title="FlyCast API",
    description="Drosophila connectome recurrent reservoir computing engine for time-series forecasting",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS + ["*"],  # allow local dev and deployment URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck():
    """Railway / container healthcheck endpoint."""
    ready = is_brain_ready()
    if not ready:
        return {
            "status": "initializing",
            "brain_loaded": False,
            "stage": "building_connectome",
        }
    try:
        brain = get_brain()
        return {
            "status": "ok",
            "brain_loaded": True,
            "brain_version": brain.manifest.dataset,
            "runtime_neurons": brain.num_neurons,
            "runtime_edges": brain.num_edges,
        }
    except Exception as e:
        return {
            "status": "error",
            "brain_loaded": False,
            "detail": str(e),
        }


# Register v1 routes
app.include_router(brain_router, prefix="/api/v1")
app.include_router(demos_router, prefix="/api/v1")
app.include_router(experiments_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
