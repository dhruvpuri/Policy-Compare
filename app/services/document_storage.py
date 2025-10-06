"""Document storage service for managing document persistence."""

from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.document import Document, ProcessingStatus


class DocumentStorageService:
    """Service for storing and retrieving documents."""
    
    def __init__(self):
        """Initialize the storage service."""
        # In-memory storage for now (can be replaced with database)
        self._documents: Dict[str, Document] = {}
    
    async def save_document(self, document: Document) -> Document:
        """Save a document to storage.
        
        Args:
            document: Document to save
            
        Returns:
            Saved document
        """
        self._documents[document.id] = document
        return document
    
    async def store_document(self, document: Document) -> Document:
        """Store a document to storage (alias for save_document).
        
        Args:
            document: Document to store
            
        Returns:
            Stored document
        """
        return await self.save_document(document)
    
    async def update_document(self, document_id: str, document: Document) -> Document:
        """Update a document in storage.
        
        Args:
            document_id: Document identifier
            document: Document to update
            
        Returns:
            Updated document
        """
        self._documents[document_id] = document
        return document
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document if found, None otherwise
        """
        return self._documents.get(document_id)
    
    async def list_documents(self) -> List[Document]:
        """List all documents.
        
        Returns:
            List of all documents
        """
        return list(self._documents.values())
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if deleted, False if not found
        """
        if document_id in self._documents:
            del self._documents[document_id]
            return True
        return False
    
    async def update_document_status(self, document_id: str, status: ProcessingStatus) -> Optional[Document]:
        """Update document processing status.
        
        Args:
            document_id: Document identifier
            status: New processing status
            
        Returns:
            Updated document if found, None otherwise
        """
        if document_id in self._documents:
            self._documents[document_id].processing_status = status
            self._documents[document_id].updated_at = datetime.utcnow()
            return self._documents[document_id]
        return None
    
    async def get_documents_by_status(self, status: ProcessingStatus) -> List[Document]:
        """Get documents by processing status.
        
        Args:
            status: Processing status to filter by
            
        Returns:
            List of documents with the specified status
        """
        return [doc for doc in self._documents.values() if doc.processing_status == status]
    
    async def search_documents(self, query: str) -> List[Document]:
        """Search documents by filename or content.
        
        Args:
            query: Search query
            
        Returns:
            List of matching documents
        """
        results = []
        query_lower = query.lower()
        
        for document in self._documents.values():
            # Search in filename
            if (document.metadata and 
                document.metadata.filename and 
                query_lower in document.metadata.filename.lower()):
                results.append(document)
                continue
            
            # Search in extracted facts
            if (document.content and 
                document.content.extracted_facts):
                for fact in document.content.extracted_facts:
                    if (query_lower in fact.key.lower() or 
                        query_lower in fact.value.lower()):
                        results.append(document)
                        break
        
        return results
