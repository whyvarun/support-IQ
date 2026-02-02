"""
SupportIQ: IT Support Automation via Tiered RAG
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from app.config import get_settings
from app.api.routes import router
from app.database.connection import close_db
from app import __version__

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
STATIC_DIR = PROJECT_ROOT / "static"

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initializes ML models on startup, cleans up on shutdown.
    """
    # Startup: Models are loaded lazily on first use (singleton pattern)
    print(f"Starting SupportIQ v{__version__}")
    print(f"Database: {settings.database_url[:50]}...")
    
    # Pre-load models to avoid first-request latency
    print("Loading ML models (MiniLM + BERT)... This may take 1-2 minutes...")
    from app.services.semantic_search import semantic_search_service
    from app.services.sentiment import sentiment_analyzer
    _ = semantic_search_service  # Triggers initialization
    _ = sentiment_analyzer
    
    print("All models loaded successfully!")
    
    yield
    
    # Shutdown: Clean up resources
    print("🛑 Shutting down SupportIQ...")
    await close_db()
    print("👋 Goodbye!")


# Create FastAPI application
app = FastAPI(
    title="SupportIQ",
    description="""
## IT Support Automation via Tiered RAG

SupportIQ is an intelligent IT support automation platform featuring:

### 🔍 Semantic Search (MiniLM)
- Hybrid search combining semantic similarity and keyword matching
- 384-dimensional embeddings for accurate query understanding

### 🎯 BERT Sentiment Analysis
- Automatic sentiment detection for incoming tickets
- Dynamic urgency scoring (1-10) based on sentiment and keywords

### 📚 Tiered Knowledge Base
- **L1**: FAQ/Common Issues (self-service)
- **L2**: Technical Guides (moderate complexity)
- **L3**: Expert Solutions (specialist knowledge)

### 🔄 Auto-Promotion
- Automatically promotes frequently resolved solutions
- L3 → L2 when resolved >10 times with high feedback
- L2 → L1 when resolved >25 times with high feedback
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix=settings.api_prefix)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Root endpoint - serve the Query Resolution UI
@app.get("/")
async def root():
    """Serve the Query Resolution UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "name": "SupportIQ",
        "version": __version__,
        "description": "IT Support Automation via Tiered RAG",
        "docs": "/docs",
        "features": [
            "MiniLM Semantic Search",
            "BERT Sentiment Analysis",
            "Dynamic Urgency Scoring (1-10)",
            "Tiered Knowledge Base (L1/L2/L3)",
            "Auto-Promotion Engine"
        ],
        "endpoints": {
            "tickets": f"{settings.api_prefix}/tickets",
            "search": f"{settings.api_prefix}/search",
            "knowledge": f"{settings.api_prefix}/knowledge",
            "analytics": f"{settings.api_prefix}/analytics",
            "health": f"{settings.api_prefix}/health"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
