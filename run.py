# run.py - Place in root directory
import subprocess
import sys
import os

def run_backend():
    """Run FastAPI backend"""
    print("Starting FastAPI backend...")
    subprocess.Popen([
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", "0.0.0.0", "--port", "8000", "--reload"
    ])

def run_frontend():
    """Run Streamlit frontend"""
    print("Starting Streamlit frontend...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "frontend/streamlit_app.py", "--server.port", "8501"
    ])

if __name__ == "__main__":
    print("🚀 Starting Menu Extraction System")
    print("=" * 50)

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")

    # Start backend
    run_backend()

    # Wait a bit for backend to initialize
    import time
    time.sleep(3)

    # Start frontend
    run_frontend()