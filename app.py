import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import os
from pathlib import Path

from src.config import HOST, PORT, STATIC_DIR

app = FastAPI(
    title="Transaction Risk Investigation Assistant",
    description="Bank Fraud Desk Risk Engine & AI Grounded Investigation Assistant (NexusTiQ 24 TRACK_ID=PS6)",
    version="1.0.0"
)

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "track_id": "PS6",
        "app": "Transaction Risk Investigation Assistant"
    }

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Transaction Risk Investigation Assistant</h1><p>NexusTiQ 24 TRACK_ID=PS6</p>")

if __name__ == "__main__":
    print(f"🚀 Starting Transaction Risk Investigation Assistant on http://localhost:{PORT}")
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
