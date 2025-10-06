"""Document models for the bank comparator application."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    """Supported document formats."""
    PDF = "pdf"
    TEXT = "text"
    DOCX = "docx"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentMetadata(BaseModel):
    """Metadata for uploaded documents."""
    filename: str
    file_size: int
    format: DocumentFormat
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    bank_name: Optional[str] = None
    document_type: Optional[str] = None


class ExtractedFact(BaseModel):
    """Represents a single extracted fact from a document."""
    key: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_page: Optional[int] = None
    source_text: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # For precise location tracking
    source_reference: Optional[str] = None  # filename + page/line reference
    effective_date: Optional[str] = None  # Document effective date if found


class DocumentContent(BaseModel):
    """Processed document content."""
    raw_text: str
    cleaned_text: str
    page_count: Optional[int] = None
    extracted_facts: List[ExtractedFact] = Field(default_factory=list)
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Complete document representation."""
    id: str
    metadata: DocumentMetadata
    content: Optional[DocumentContent] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""
    document_id: str
    status: str
    message: str


class ComparisonStatus(str, Enum):
    """Status for fact comparison."""
    SAME = "same"
    DIFFERENT = "different"
    MISSING = "missing"
    SUSPECT = "suspect"


class FactComparison(BaseModel):
    """Comparison result for a specific fact across documents."""
    fact_key: str
    status: ComparisonStatus
    values: Dict[str, Optional[str]]  # document_id -> value
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    evidence: Dict[str, Optional[str]] = Field(default_factory=dict)  # source text


class DocumentComparison(BaseModel):
    """Complete comparison result between multiple documents."""
    comparison_id: str
    document_ids: List[str]
    fact_comparisons: List[FactComparison]
    summary: Dict[str, int]  # Status counts
    created_at: datetime = Field(default_factory=datetime.utcnow)
