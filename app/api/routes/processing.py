"""Processing routes for document analysis status."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter(prefix="/processing", tags=["processing"])


@router.get("/status")
async def get_processing_status():
    """Get overall processing status."""
    return {
        "status": "active",
        "service": "document-processing",
        "message": "Processing service is running"
    }


@router.get("/queue")
async def get_processing_queue():
    """Get processing queue status."""
    return {
        "queue_length": 0,
        "processing": 0,
        "completed_today": 0,
        "failed_today": 0
    }



