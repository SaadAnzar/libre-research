from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime

# Import routers
from app.routers import research, auth, users

load_dotenv()

app = FastAPI(
    title="Libre Research",
    description="A platform for conducting deep research and generating comprehensive reports.",
    version="0.1.0",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://libre-research.vercel.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    print("Root Endpoint was called")
    return {"message": "Welcome to Libre Research"}


@app.get("/health")
async def health_check():
    print("Health check endpoint was called!")
    return {"status": "healthy"}


@app.get("/api/test")
async def test_endpoint():
    """Test endpoint that doesn't require authentication"""
    print("Test endpoint was called!")
    return {
        "message": "Test endpoint successful",
        "success": True,
        "timestamp": str(datetime.now()),
    }


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
