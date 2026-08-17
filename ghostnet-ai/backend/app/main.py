import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.database import engine, Base
from app.websocket import ws_manager
from app.routers import readings, coverage, help_points, sos, checkin, predictions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghostnet")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes PostGIS extensions and creates DB tables on startup."""
    logger.info("Initializing GhostNet database and PostGIS extension...")
    try:
        async with engine.begin() as conn:
            # Enable PostGIS extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
    yield
    logger.info("Shutting down GhostNet backend...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(readings.router, prefix=settings.API_V1_STR)
app.include_router(coverage.router, prefix=settings.API_V1_STR)
app.include_router(help_points.router, prefix=settings.API_V1_STR)
app.include_router(sos.router, prefix=settings.API_V1_STR)
app.include_router(checkin.router, prefix=settings.API_V1_STR)
app.include_router(predictions.router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker / orchestration probes."""
    return {
        "status": "healthy",
        "service": "ghostnet-backend",
        "version": settings.VERSION,
        "demo_district": settings.DEMO_DISTRICT,
        "sms_gateway_mode": settings.SMS_GATEWAY_MODE,
        "mesh_mode": settings.MESH_MODE,
    }


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket endpoint for live signal telemetry,
    emergency SOS alerts, and ML prediction updates.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive loop
            data = await websocket.receive_text()
            logger.debug(f"Received from client: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)
