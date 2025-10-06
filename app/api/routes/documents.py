"""Document-related API routes."""

import os
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.models.document import Document, DocumentUploadResponse
from app.services.document_ingestion import DocumentIngestionService
from app.services.document_storage import DocumentStorageService
from app.services.enhanced_document_processor import EnhancedDocumentProcessor
from app.services.llm_service import LLMExtractionService
from app.services.normalization_service import NormalizationService

router = APIRouter(prefix="/documents", tags=["documents"])

# Initialize services
storage_service = DocumentStorageService()
normalization_service = NormalizationService()

# Initialize LLM service if API key is available
llm_service = None
try:
    if os.getenv("GOOGLE_API_KEY"):
        llm_service = LLMExtractionService()
        print("✅ LLM service initialized with Gemini API")
    else:
        print("⚠️  No GOOGLE_API_KEY found - LLM features disabled")
except Exception as e:
    print(f"⚠️  Failed to initialize LLM service: {e}")

# Initialize enhanced processor with extraction mode toggle
import os
extraction_mode = os.getenv("EXTRACTION_MODE", "smart").lower()
if extraction_mode not in ("smart", "rule", "hybrid", "llm"):
    extraction_mode = "smart"

enhanced_processor = EnhancedDocumentProcessor(
    storage_service=storage_service,
    llm_service=llm_service,
    normalization_service=normalization_service,
    extraction_mode=extraction_mode
)

# Initialize ingestion service with enhanced processing and shared storage
ingestion_service = DocumentIngestionService(
    enhanced_processor=enhanced_processor,
    storage_service=storage_service  # Pass the SAME storage service instance
)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document.
    
    Args:
        file: The document file to upload
        
    Returns:
        Upload response with document ID and status
    """
    try:
        document = await ingestion_service.ingest_document(file)
        
        if document.status.value == "failed":
            return DocumentUploadResponse(
                document_id=document.id,
                status="error",
                message=f"Document processing failed: {document.error_message}"
            )
        
        return DocumentUploadResponse(
            document_id=document.id,
            status="success",
            message="Document uploaded and processed successfully"
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{document_id}", response_model=Document)
async def get_document(document_id: str):
    """Get document by ID.
    
    Args:
        document_id: The document ID
        
    Returns:
        Document object with content and metadata
    """
    document = await storage_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/", response_model=List[Document])
async def list_documents(limit: int = 50, offset: int = 0):
    """List all uploaded documents.
    
    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        
    Returns:
        List of document metadata
    """
    return await storage_service.list_documents(limit=limit, offset=offset)


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document.
    
    Args:
        document_id: The document ID to delete
        
    Returns:
        Success message
    """
    success = await storage_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": f"Document {document_id} deleted successfully"}


@router.get("/{document_id}/content")
async def get_document_content(document_id: str):
    """Get the extracted content of a document.
    
    Args:
        document_id: The document ID
        
    Returns:
        Document content with extracted text and facts
    """
    document = await storage_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.content:
        raise HTTPException(status_code=404, detail="No content available for this document")
    
    return {
        "document_id": document_id,
        "raw_text": document.content.raw_text,
        "cleaned_text": document.content.cleaned_text,
        "extracted_facts": document.content.extracted_facts,
        "processing_metadata": document.content.processing_metadata,
        "page_count": document.content.page_count
    }
