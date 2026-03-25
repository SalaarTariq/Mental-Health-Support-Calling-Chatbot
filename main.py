"""
CalmLink — Entry Point
Starts the FastAPI backend server.
Run with: python main.py
"""

import uvicorn
from backend.config import BACKEND_HOST, BACKEND_PORT, validate_config


def main():
    validate_config()
    print(f"Starting CalmLink backend on {BACKEND_HOST}:{BACKEND_PORT}")
    uvicorn.run(
        "backend.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
