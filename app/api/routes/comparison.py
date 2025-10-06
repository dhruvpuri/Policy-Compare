"""Comparison-related API routes."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.document import DocumentComparison
from app.services.document_storage import DocumentStorageService
from app.services.normalization_service import NormalizationService

# Use the SAME in-memory storage instance as the upload routes
# to avoid "Document not found" during comparison.
try:
    # Import the shared storage instance created in documents.py
    from app.api.routes.documents import storage_service as _shared_storage_service  # type: ignore
    SHARED_STORAGE = _shared_storage_service
except Exception:
    # Fallback: create a local instance (useful for unit tests)
    SHARED_STORAGE = DocumentStorageService()

router = APIRouter(prefix="/comparison", tags=["comparison"])

# Initialize services (reuse shared in-memory storage)
storage_service = SHARED_STORAGE
normalization_service = NormalizationService()


class ComparisonRequest(BaseModel):
    """Request model for document comparison."""
    document_ids: List[str]
    comparison_fields: List[str] = []  # Optional: specific fields to compare


@router.post("/compare")
async def compare_documents(request: ComparisonRequest):
    """Compare multiple documents and generate comparison report.
    
    Args:
        request: Comparison request with document IDs and optional fields
        
    Returns:
        Document comparison result with side-by-side analysis
    """
    if len(request.document_ids) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 documents required for comparison"
        )
    
    if len(request.document_ids) > 4:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 4 documents can be compared at once"
        )
    
    try:
        # Fetch all documents
        documents = []
        for doc_id in request.document_ids:
            doc = await storage_service.get_document(doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
            if doc.status != "completed":
                raise HTTPException(status_code=400, detail=f"Document {doc_id} is not fully processed")
            documents.append(doc)
        
        # Generate comparison
        comparison_result = await generate_fact_comparison(documents)
        return comparison_result
        
    except Exception as e:
        print(f"❌ Comparison API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


async def generate_fact_comparison(documents: List) -> Dict[str, Any]:
    """Generate comparison table from document facts."""
    
    print(f"🔍 Generating comparison for {len(documents)} documents...")
    
    # Collect all unique fact keys
    all_fact_keys = set()
    doc_facts = {}
    
    for i, doc in enumerate(documents):
        try:
            print(f"📄 Processing document {i+1}: {type(doc)}")
            
            doc_id = doc.id
            doc_name = doc.metadata.filename if hasattr(doc, 'metadata') and doc.metadata else f"Document {doc_id[:8]}"
            facts = {}
            
            print(f"   - ID: {doc_id}")
            print(f"   - Name: {doc_name}")
            print(f"   - Has content: {hasattr(doc, 'content') and doc.content is not None}")
            
            if hasattr(doc, 'content') and doc.content and hasattr(doc.content, 'extracted_facts') and doc.content.extracted_facts:
                print(f"   - Facts count: {len(doc.content.extracted_facts)}")
                for fact in doc.content.extracted_facts:
                    # Safely handle optional fields (source_text can be None)
                    safe_source_text = getattr(fact, 'source_text', '') or ''

                    facts[fact.key] = {
                        "value": fact.value,
                        "confidence": fact.confidence,
                        "source_text": safe_source_text,
                        "source_reference": getattr(fact, 'source_reference', None),
                        "effective_date": getattr(fact, 'effective_date', None)
                    }
                    all_fact_keys.add(fact.key)
            else:
                print(f"   - No facts found")
            
            doc_facts[doc_id] = {
                "name": doc_name,
                "facts": facts
            }
        except Exception as e:
            print(f"❌ Error processing document {i+1}: {str(e)}")
            raise
    
    # Build comparison table
    comparison_table = []
    
    for fact_key in sorted(all_fact_keys):
        row = {
            "fact_key": fact_key,
            "section": fact_key.split('.')[0].replace('_', ' ').title(),
            "field": fact_key.split('.')[1] if '.' in fact_key else fact_key,
            "documents": {}
        }
        
        values = []
        for doc_id in doc_facts:
            doc_name = doc_facts[doc_id]["name"]
            fact = doc_facts[doc_id]["facts"].get(fact_key)
            
            if fact:
                src_text = (fact.get("source_text") or "")
                row["documents"][doc_name] = {
                    "value": fact.get("value"),
                    "confidence": fact.get("confidence", 0),
                    "source_text": (src_text[:100] + "...") if len(src_text) > 100 else src_text,
                    "source_reference": fact.get("source_reference"),
                    "effective_date": fact.get("effective_date"),
                    "status": "found"
                }
                values.append(fact["value"])
            else:
                row["documents"][doc_name] = {
                    "value": "Not found",
                    "confidence": 0,
                    "source_text": "",
                    "status": "missing"
                }
        
        # Determine comparison status with conflict detection (Assignment req: Suspect for conflicts)
        # CRITICAL FIX: Check actual document status, not just values array
        unique_values = set(v for v in values if v and v.strip())  # Non-empty values
        total_docs = len(doc_facts)
        docs_with_data = len(values)  # Count of docs that had this fact
        docs_missing = total_docs - docs_with_data
        
        print(f"   Status debug for {fact_key}: total_docs={total_docs}, docs_with_data={docs_with_data}, unique_values={len(unique_values)}")
        
        if docs_missing > 0 and docs_with_data > 0:
            # Some documents have the fact, others don't -> Different
            row["comparison_status"] = "different"
            print(f"     -> DIFFERENT (mixed: {docs_with_data} have data, {docs_missing} missing)")
        elif docs_missing == total_docs:
            # All documents missing this fact -> Missing
            row["comparison_status"] = "missing"
            print(f"     -> MISSING (all {total_docs} docs missing)")
        elif len(unique_values) == 1:
            # All documents have the same non-empty value -> Same
            row["comparison_status"] = "same" 
            print(f"     -> SAME (all {docs_with_data} docs have same value)")
        elif len(unique_values) > 1:
            # Multiple different values - usually just "different", not "suspect"
            # Only mark as "suspect" for truly contradictory ranges/overlaps
            row["comparison_status"] = "different"
            print(f"     -> DIFFERENT (multiple unique values: {unique_values})")
            
            # TODO: Reserve "suspect" for numerical ranges that overlap contradictorily
            # e.g., "10%-15%" vs "12%-18%" (overlapping ranges)
            # Simple different values like "RPLR" vs "IHPLR" are just different banks
        
        comparison_table.append(row)
    
    return {
        "comparison_id": f"comp_{documents[0].id[:8]}_{len(documents)}docs",
        "document_count": len(documents),
        "document_names": [doc_facts[doc_id]["name"] for doc_id in doc_facts],
        "total_facts": len(comparison_table),
        "same_facts": len([r for r in comparison_table if r["comparison_status"] == "same"]),
        "different_facts": len([r for r in comparison_table if r["comparison_status"] == "different"]),
        "missing_facts": len([r for r in comparison_table if r["comparison_status"] == "missing"]),
        "suspect_facts": len([r for r in comparison_table if r["comparison_status"] == "suspect"]),
        "comparison_table": comparison_table
    }


@router.get("/{comparison_id}", response_model=DocumentComparison)
async def get_comparison(comparison_id: str):
    """Get comparison result by ID.
    
    Args:
        comparison_id: The comparison ID
        
    Returns:
        Document comparison result
    """
    # TODO: Implement comparison retrieval
    raise HTTPException(
        status_code=501, 
        detail="Comparison retrieval not implemented yet"
    )


@router.get("/", response_model=List[DocumentComparison])
async def list_comparisons():
    """List all comparison results.
    
    Returns:
        List of comparison summaries
    """
    # TODO: Implement comparison listing
    return []

@router.post("/export/csv")
async def export_comparison_csv(request: ComparisonRequest):
    """Export comparison results as CSV.
    
    Args:
        request: Comparison request with document IDs
        
    Returns:
        CSV data as string
    """
    from app.services.export_service import ExportService
    
    if len(request.document_ids) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 documents required for comparison"
        )
    
    try:
        # Get documents
        documents = []
        for doc_id in request.document_ids:
            doc = storage_service.get_document(doc_id)
            if not doc:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Document {doc_id} not found"
                )
            
            # Convert to dict format expected by ExportService
            doc_dict = {
                'metadata': {
                    'filename': doc.metadata.filename,
                    'bank_name': getattr(doc.metadata, 'bank_name', 'Unknown'),
                    'file_size': doc.metadata.file_size
                },
                'status': doc.status,
                'content': {
                    'extracted_facts': [
                        {
                            'key': fact.key,
                            'value': fact.value,
                            'confidence': fact.confidence,
                            'source_text': getattr(fact, 'source_text', ''),
                            'source_reference': getattr(fact, 'source_reference', '')
                        }
                        for fact in doc.content.extracted_facts
                    ] if doc.content else [],
                    'processing_metadata': {}
                },
                'created_at': doc.created_at.isoformat() if doc.created_at else None
            }
            documents.append(doc_dict)
        
        # Generate CSV
        csv_data = ExportService.generate_csv_export(documents)
        
        return {
            "status": "success",
            "format": "csv",
            "data": csv_data,
            "filename": f"butter_money_comparison_{len(documents)}docs.csv"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating CSV export: {str(e)}"
        )


@router.post("/export/json")
async def export_comparison_json(request: ComparisonRequest):
    """Export comparison results as JSON.
    
    Args:
        request: Comparison request with document IDs
        
    Returns:
        JSON data as string
    """
    from app.services.export_service import ExportService
    
    if len(request.document_ids) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 documents required for comparison"
        )
    
    try:
        # Get documents
        documents = []
        for doc_id in request.document_ids:
            doc = storage_service.get_document(doc_id)
            if not doc:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Document {doc_id} not found"
                )
            
            # Convert to dict format expected by ExportService
            doc_dict = {
                'metadata': {
                    'filename': doc.metadata.filename,
                    'bank_name': getattr(doc.metadata, 'bank_name', 'Unknown'),
                    'file_size': doc.metadata.file_size
                },
                'status': doc.status,
                'content': {
                    'extracted_facts': [
                        {
                            'key': fact.key,
                            'value': fact.value,
                            'confidence': fact.confidence,
                            'source_text': getattr(fact, 'source_text', ''),
                            'source_reference': getattr(fact, 'source_reference', '')
                        }
                        for fact in doc.content.extracted_facts
                    ] if doc.content else [],
                    'processing_metadata': {}
                },
                'created_at': doc.created_at.isoformat() if doc.created_at else None
            }
            documents.append(doc_dict)
        
        # Generate JSON
        json_data = ExportService.generate_json_export(documents)
        
        return {
            "status": "success",
            "format": "json",
            "data": json_data,
            "filename": f"butter_money_comparison_{len(documents)}docs.json"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating JSON export: {str(e)}"
        )