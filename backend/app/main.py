"""FaceAttend API — FastAPI application entry point.

Initialises the FastAPI app with middleware, routers, and lifespan events.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import Base, engine
from app.routers import attendance, auth, dashboard, face, users

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Creates database tables on startup if they do not exist.
    """
    logger.info("Starting FaceAttend API...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")
    yield
    await engine.dispose()
    logger.info("FaceAttend API shut down.")


app = FastAPI(
    title="FaceAttend API",
    description="Modèle de reconnaissance faciale dédié à la gestion du pointage et de la présence",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(face.router, prefix="/api/v1/face", tags=["Face Recognition"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint returning API information.

    Returns:
        dict: API name, version, and docs URL.
    """
    return {
        "name": "FaceAttend API",
        "version": "1.0.0",
        "docs": "/docs",
    }
