"""
FastAPI Main Application
English Video Learning Platform Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from core.config import settings
from core.database import init_db
from api import auth, videos, admin, vocabulary, search, clips, subtitles

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for English Video Learning Platform with AI-powered features",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting English Video Learning Platform API...")
    init_db()
    print(f"✅ API running on {settings.API_URL}")


# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to English Video Learning Platform API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": f"{settings.API_URL}/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "ok", "service": "backend-api"}


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(vocabulary.router, prefix="/api/vocabulary", tags=["Vocabulary"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(clips.router, prefix="/api/clips", tags=["Clips"])
app.include_router(subtitles.router, prefix="/api/subtitles", tags=["Subtitles"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
