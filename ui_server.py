"""
Simple static file server for the SupportIQ UI.
Use this for quick UI testing without waiting for ML models to load.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Project paths
PROJECT_ROOT = Path(__file__).parent
STATIC_DIR = PROJECT_ROOT / "static"

app = FastAPI(title="SupportIQ UI Server")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    """Serve the Query Resolution UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"error": "index.html not found", "static_dir": str(STATIC_DIR)}

# Mock API endpoints for UI testing
@app.post("/api/v1/tickets")
async def mock_create_ticket(data: dict = None):
    """Mock ticket creation for UI testing."""
    return {
        "ticket": {
            "id": 42,
            "title": "Test Ticket",
            "description": "Test description",
            "status": "open",
            "urgency_score": 7,
            "urgency_level": "high",
            "sentiment_score": -0.6,
            "sentiment_label": "negative",
            "category": "email",
            "assigned_tier": "L2",
            "user_email": "test@example.com",
            "created_at": "2026-02-01T23:00:00Z",
            "updated_at": None,
            "resolved_at": None
        },
        "urgency_analysis": {
            "score": 7,
            "level": "high",
            "assigned_tier": "L2",
            "factors": {
                "sentiment_weight": 0.3,
                "keyword_weight": 0.4,
                "category_weight": 0.3
            },
            "explanation": "High urgency due to email access issues affecting work productivity."
        },
        "sentiment_analysis": {
            "label": "negative",
            "score": -0.6,
            "confidence": 0.89
        },
        "suggested_solutions": [
            {
                "id": 1,
                "tier": "L1",
                "title": "Restart Outlook and Reconnect to Server",
                "content": "1. Close Outlook completely\n2. Press Windows + R, type 'outlook.exe /resetnavpane' and press Enter\n3. Wait for Outlook to restart\n4. If the issue persists, go to File > Account Settings and click 'Repair'",
                "keywords": ["outlook", "email", "sync", "restart"],
                "category": "email",
                "usage_count": 156,
                "avg_feedback_score": 4.5,
                "semantic_score": 0.92,
                "keyword_score": 0.85,
                "hybrid_score": 0.89
            },
            {
                "id": 2,
                "tier": "L2",
                "title": "Reset Outlook Profile Configuration",
                "content": "1. Go to Control Panel > Mail > Show Profiles\n2. Click 'Remove' to delete the corrupted profile\n3. Click 'Add' to create a new profile\n4. Enter your email account credentials\n5. Set the new profile as default",
                "keywords": ["outlook", "profile", "email", "configuration"],
                "category": "email",
                "usage_count": 89,
                "avg_feedback_score": 4.2,
                "semantic_score": 0.85,
                "keyword_score": 0.78,
                "hybrid_score": 0.82
            },
            {
                "id": 3,
                "tier": "L1",
                "title": "Clear Outlook Cache Files",
                "content": "1. Close Outlook\n2. Navigate to %localappdata%\\Microsoft\\Outlook\n3. Delete all .ost files (these will regenerate)\n4. Restart Outlook and allow it to resync\n5. This may take several minutes for large mailboxes",
                "keywords": ["outlook", "cache", "ost", "sync"],
                "category": "email",
                "usage_count": 234,
                "avg_feedback_score": 4.7,
                "semantic_score": 0.78,
                "keyword_score": 0.82,
                "hybrid_score": 0.80
            }
        ],
        "message": "Ticket created successfully with AI analysis"
    }

if __name__ == "__main__":
    print("🚀 Starting SupportIQ UI Server (lightweight mode)")
    print(f"📁 Static files: {STATIC_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=3000)
