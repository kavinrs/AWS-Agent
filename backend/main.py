"""
Main entrypoint — run with:  python main.py
Or with uvicorn:             uvicorn main:app --reload --port 8000
"""
import uvicorn
from api.app import app

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
