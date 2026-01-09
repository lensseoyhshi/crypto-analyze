"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .core.config import settings
from .services import scheduler
from .api.routes import data

# Configure logging
logging.basicConfig(
	level=logging.INFO if not settings.DEBUG else logging.DEBUG,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Application lifespan manager for startup and shutdown events."""
	# Startup
	logger.info(f"Starting {settings.APP_NAME}")
	scheduler.start_background_tasks(app)
	logger.info("Application started successfully")
	
	yield
	
	# Shutdown
	logger.info("Shutting down application")
	await scheduler.stop_background_tasks()
	logger.info("Application shutdown complete")


app = FastAPI(
	title=settings.APP_NAME,
	debug=settings.DEBUG,
	lifespan=lifespan,
	description="Cryptocurrency data collection and analysis platform",
	version="1.0.0"
)

# Include routers
app.include_router(data.router)


@app.get("/health")
def health_check():
	"""Health check endpoint."""
	return {
		"status": "ok",
		"app": settings.APP_NAME,
		"debug": settings.DEBUG
	}


@app.get("/")
def root():
	"""Root endpoint."""
	return {
		"message": "Crypto Analyze API",
		"docs": "/docs",
		"health": "/health",
		"data": {
			"responses": "/data/responses",
			"stats": "/data/stats",
			"sources": "/data/sources"
		}
	}


