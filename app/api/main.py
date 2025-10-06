"""Main FastAPI application."""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load environment variables first, before importing routes
load_dotenv()
print(f"🔧 Environment loaded - API Key present: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")

from app.api.routes import documents, comparison, processing

app = FastAPI(
    title="Multi-Bank Policy Comparator API",
    description="API for processing and comparing bank MITC documents with LLM-powered fact extraction",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api/v1")
app.include_router(comparison.router, prefix="/api/v1")
app.include_router(processing.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Multi-Bank Policy Comparator API", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "bank-comparator-api",
        "version": "1.0.0"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "detail": str(exc)}
    )
