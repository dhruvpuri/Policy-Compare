"""Enhanced document processing pipeline with LLM integration."""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.document import Document, ProcessingStatus, DocumentContent
from app.services.document_storage import DocumentStorageService
from app.services.llm_service import LLMExtractionService
from app.services.normalization_service import NormalizationService
from app.services.rule_based_extraction import RuleBasedExtractionService
from app.services.smart_extraction_service import SmartExtractionService


class EnhancedDocumentProcessor:
    """Enhanced document processing pipeline."""
    
    def __init__(
        self,
        storage_service: DocumentStorageService,
        llm_service: Optional[LLMExtractionService] = None,
        normalization_service: Optional[NormalizationService] = None,
        extraction_mode: str = "smart"  # smart | rule | hybrid | llm
    ):
        """Initialize the enhanced processor.
        
        Args:
            storage_service: Document storage service
            llm_service: LLM extraction service (optional)
            normalization_service: Normalization service (optional)
            extraction_mode: Extraction mode (smart=rule+targeted_llm, rule=only_rules, hybrid=rule+full_llm, llm=only_llm)
        """
        self.storage = storage_service
        self.llm_service = llm_service
        self.normalization_service = normalization_service or NormalizationService()
        self.rule_service = RuleBasedExtractionService()
        self.smart_service = SmartExtractionService(llm_service, normalization_service)
        self.extraction_mode = extraction_mode
        
        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "facts_extracted": 0,
            "conflicts_detected": 0
        }
    
    async def process_document(self, document: Document) -> Document:
        """Process a document through the complete pipeline.
        
        Args:
            document: Document to process
            
        Returns:
            Processed document with extracted facts
        """
        try:
            # Update status to processing
            document.status = ProcessingStatus.PROCESSING
            await self.storage.store_document(document)
            
            # Step 1: Analyze document structure (if LLM available)
            if self.llm_service and document.content:
                structure_analysis = await self.llm_service.analyze_document_structure(
                    document.content.cleaned_text
                )
                
                # Update metadata based on analysis
                if structure_analysis.get("bank_name"):
                    document.metadata.bank_name = structure_analysis["bank_name"]
                if structure_analysis.get("document_type"):
                    document.metadata.document_type = structure_analysis["document_type"]
                
                # Store analysis in processing metadata
                if not document.content.processing_metadata:
                    document.content.processing_metadata = {}
                document.content.processing_metadata["structure_analysis"] = structure_analysis
            
            # Step 2: Extract facts using smart extraction or fallback modes
            normalized_facts = []
            if document.content:
                text = document.content.cleaned_text
                filename = document.metadata.filename if document.metadata else "unknown"
                
                if self.extraction_mode == "smart":
                    # NEW: Smart extraction - rules first, then targeted LLM for gaps
                    print(f"🧠 Using SMART extraction for {filename}")
                    normalized_facts = await self.smart_service.extract_facts_smart(text, filename, document.id)
                
                elif self.extraction_mode == "rule":
                    # Rule-based only
                    print(f"🔧 Using RULE-ONLY extraction for {filename}")
                    rule_facts = self.rule_service.extract(text, filename=filename)
                    normalized_facts = self.normalization_service.normalize_facts(rule_facts)
                
                elif self.extraction_mode == "llm" and self.llm_service:
                    # LLM only
                    print(f"🤖 Using LLM-ONLY extraction for {filename}")
                    llm_facts = await self.llm_service.extract_facts(text, document.id)
                    normalized_facts = self.normalization_service.normalize_facts(llm_facts)
                
                elif self.extraction_mode == "hybrid" and self.llm_service:
                    # Traditional hybrid - rule + full LLM
                    print(f"🔄 Using HYBRID extraction for {filename}")
                    rule_facts = self.rule_service.extract(text, filename=filename)
                    llm_facts = await self.llm_service.extract_facts(text, document.id)
                    raw_facts = rule_facts + llm_facts
                    normalized_facts = self.normalization_service.normalize_facts(raw_facts)
                
                else:
                    print(f"⚠️  No extraction performed - mode: {self.extraction_mode}, LLM available: {self.llm_service is not None}")
                    normalized_facts = []
                document.content.extracted_facts = normalized_facts
                
                # Step 4: Detect conflicts
                conflicts = self.normalization_service.detect_conflicts(normalized_facts)
                document.content.processing_metadata["conflicts"] = conflicts
                
                # Update stats
                self.stats["facts_extracted"] += len(normalized_facts)
                self.stats["conflicts_detected"] += len(conflicts)
            
            # Step 5: Mark as completed
            document.status = ProcessingStatus.COMPLETED
            document.updated_at = datetime.utcnow()
            
            # Store final document
            await self.storage.update_document(document.id, document)
            
            # Update stats
            self.stats["total_processed"] += 1
            self.stats["successful"] += 1
            
            return document
            
        except Exception as e:
            # Mark as failed
            document.status = ProcessingStatus.FAILED
            document.error_message = str(e)
            document.updated_at = datetime.utcnow()
            
            await self.storage.update_document(document.id, document)
            
            # Update stats
            self.stats["total_processed"] += 1
            self.stats["failed"] += 1
            
            raise e
    
    async def batch_process_documents(self, document_ids: List[str]) -> Dict[str, Any]:
        """Process multiple documents in batch.
        
        Args:
            document_ids: List of document IDs to process
            
        Returns:
            Batch processing results
        """
        results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        # Process documents concurrently (with limit)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent processing
        
        async def process_single(doc_id: str):
            async with semaphore:
                try:
                    document = await self.storage.get_document(doc_id)
                    if document:
                        await self.process_document(document)
                        results["successful"] += 1
                    else:
                        results["errors"].append(f"Document {doc_id} not found")
                        results["failed"] += 1
                except Exception as e:
                    results["errors"].append(f"Error processing {doc_id}: {str(e)}")
                    results["failed"] += 1
                finally:
                    results["processed"] += 1
        
        # Execute all processing tasks
        tasks = [process_single(doc_id) for doc_id in document_ids]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics.
        
        Returns:
            Processing statistics
        """
        storage_stats = await self.storage.get_storage_stats()
        
        return {
            **self.stats,
            **storage_stats,
            "success_rate": (
                self.stats["successful"] / max(self.stats["total_processed"], 1) * 100
            ),
            "llm_available": self.llm_service is not None
        }
    
    async def reprocess_failed_documents(self) -> Dict[str, Any]:
        """Reprocess all failed documents.
        
        Returns:
            Reprocessing results
        """
        failed_docs = await self.storage.get_documents_by_status(ProcessingStatus.FAILED)
        
        if not failed_docs:
            return {"message": "No failed documents to reprocess", "processed": 0}
        
        # Reset status and reprocess
        for doc in failed_docs:
            doc.status = ProcessingStatus.PENDING
            doc.error_message = None
            await self.storage.update_document(doc.id, doc)
        
        document_ids = [doc.id for doc in failed_docs]
        results = await self.batch_process_documents(document_ids)
        
        return {
            "message": f"Reprocessed {len(failed_docs)} failed documents",
            **results
        }
    
    async def analyze_document_quality(self, document_id: str) -> Dict[str, Any]:
        """Analyze the quality of a processed document.
        
        Args:
            document_id: Document ID to analyze
            
        Returns:
            Quality analysis results
        """
        document = await self.storage.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        if not document.content:
            return {"quality_score": 0.0, "issues": ["No content available"]}
        
        quality_analysis = {
            "quality_score": 0.0,
            "issues": [],
            "strengths": [],
            "recommendations": []
        }
        
        # Check content availability
        if document.content.cleaned_text:
            quality_analysis["strengths"].append("Text content extracted successfully")
            quality_analysis["quality_score"] += 0.3
        else:
            quality_analysis["issues"].append("No text content extracted")
        
        # Check fact extraction
        if document.content.extracted_facts:
            fact_count = len(document.content.extracted_facts)
            quality_analysis["strengths"].append(f"{fact_count} facts extracted")
            quality_analysis["quality_score"] += min(0.4, fact_count * 0.05)  # Up to 0.4 for facts
            
            # Check confidence scores
            high_confidence_facts = [f for f in document.content.extracted_facts if f.confidence > 0.8]
            if high_confidence_facts:
                quality_analysis["strengths"].append(f"{len(high_confidence_facts)} high-confidence facts")
                quality_analysis["quality_score"] += 0.2
            else:
                quality_analysis["issues"].append("Low confidence in extracted facts")
        else:
            quality_analysis["issues"].append("No facts extracted")
        
        # Check for conflicts
        conflicts = document.content.processing_metadata.get("conflicts", [])
        if conflicts:
            quality_analysis["issues"].append(f"{len(conflicts)} conflicts detected")
            quality_analysis["quality_score"] = max(0, quality_analysis["quality_score"] - len(conflicts) * 0.1)
        
        # Check structure analysis
        structure_analysis = document.content.processing_metadata.get("structure_analysis", {})
        if structure_analysis.get("quality_score", 0) > 0.7:
            quality_analysis["strengths"].append("Good document structure detected")
            quality_analysis["quality_score"] += 0.1
        
        # Generate recommendations
        if quality_analysis["quality_score"] < 0.5:
            quality_analysis["recommendations"].append("Document may need manual review")
        if not document.metadata.bank_name:
            quality_analysis["recommendations"].append("Bank name could not be identified")
        if conflicts:
            quality_analysis["recommendations"].append("Review conflicting information")
        
        # Normalize quality score to 0-1 range
        quality_analysis["quality_score"] = min(1.0, quality_analysis["quality_score"])
        
        return quality_analysis
