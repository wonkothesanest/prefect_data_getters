import pprint
from langchain_core.documents import Document
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field

class AIDocument(Document):
    """
    Enhanced Document class that inherits from langchain_core.documents.Document
    and adds domain-specific functionality for our application.
    """
    
    # Declare search_score as a proper Pydantic field
    search_score: Optional[float] = Field(default=None, description="Search relevance score")
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize AIDocument with direct inheritance from Document.
        
        Args:
            page_content: The main content of the document
            metadata: Dictionary of metadata associated with the document
            **kwargs: Additional arguments passed to parent Document class
        """
        # Extract search_score if provided in kwargs
        search_score = kwargs.pop('search_score', None)
        
        # Initialize the parent Document class
        super().__init__(page_content=page_content, metadata=metadata or {}, **kwargs)
        
        # Set search_score if provided
        if search_score is not None:
            self.search_score = search_score
    
    @property
    def document_type(self) -> str:
        """Return the document type using class name instead of manual _type_name"""
        return self.__class__.__name__
    
    def get_display_id(self) -> str:
        """
        Get the display ID for this document type.
        Override in subclasses to provide type-specific ID logic.
        """
        return getattr(self, 'id', None) or "Unknown"
    
    def _get_metadata(self, key: str, default=None):
        """Safely get a metadata value by key, returning `default` if it doesn't exist."""
        return self.metadata.get(key, default) if self.metadata else default
    
    def _context_section(self) -> str:
        """Returns the context section if present in the metadata."""
        context = self._get_metadata("context")
        if context:
            return f"""Context:
>>>>>>>>>>>>
{context}
>>>>>>>>>>>>
"""
        return ""
    
    def _format_document_string(self, fields: Dict[str, Any]) -> str:
        """
        Base formatter for document string representation.
        
        Args:
            fields: Dictionary of field names to values to display
        """
        lines = [f"Document Type: {self.document_type}"]
        
        # Add specific fields
        for key, value in fields.items():
            if value:
                lines.append(f"{key}: {value}")
        
        # Add content section
        lines.extend([
            "Content:",
            ">>>>>>>>>>>>",
            self.page_content,
            ">>>>>>>>>>>>",
            self._context_section(),
            "Additional Metadata:",
            pprint.pformat(self.metadata),
            f"END: {self.get_display_id()}",
            ">>>>>>>>>>>>",
        ])
        
        return "\n".join(lines)
    
    def __str__(self):
        """Default string representation - can be overridden by subclasses"""
        return self._format_document_string({})
    
    # Elasticsearch integration methods (basic implementation)
    def to_dict(self) -> dict:
        """Convert document to dictionary for storage"""
        return {
            'id': getattr(self, 'id', None),
            'page_content': self.page_content,
            'metadata': self.metadata,
            'document_type': self.document_type
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AIDocument':
        """Create document from dictionary"""
        # Extract search_score if present
        search_score = data.get('search_score')
        
        # Create the document with proper parameters
        doc = cls(
            page_content=data.get('page_content', ''),
            metadata=data.get('metadata', {}),
            search_score=search_score
        )
        
        # Set ID if present
        if 'id' in data and data['id']:
            doc.id = data['id']
            
        return doc
    
    def save(self, store_name: str, unified_store: Optional['UnifiedDocumentStore'] = None) -> bool:
        """
        Save this document to storage.
        
        Args:
            store_name: Name of the store/index
            unified_store: Optional UnifiedDocumentStore instance
            
        Returns:
            True if successful, False otherwise
        """
        if unified_store is None:
            from prefect_data_getters.stores.unified_document_store import UnifiedDocumentStore
            unified_store = UnifiedDocumentStore()
        
        results = unified_store.store_documents([self], store_name)
        return results['elasticsearch']['success'] > 0

    def delete(self, store_name: str, unified_store: Optional['UnifiedDocumentStore'] = None) -> bool:
        """
        Delete this document from storage.
        
        Args:
            store_name: Name of the store/index
            unified_store: Optional UnifiedDocumentStore instance
            
        Returns:
            True if successful, False otherwise
        """
        if unified_store is None:
            from .unified_document_store import UnifiedDocumentStore
            unified_store = UnifiedDocumentStore()
        
        return unified_store.delete_document(self.get_display_id(), store_name)

    @classmethod
    def search(cls, query: str, store_name: str, top_k: int = 10,
              unified_store: Optional['UnifiedDocumentStore'] = None) -> List['AIDocument']:
        """
        Search for documents of this type.
        
        Args:
            query: Search query string
            store_name: Name of the store/index
            top_k: Maximum number of results
            unified_store: Optional UnifiedDocumentStore instance
            
        Returns:
            List of AIDocument instances
        """
        if unified_store is None:
            from .unified_document_store import UnifiedDocumentStore
            unified_store = UnifiedDocumentStore()
        
        return unified_store.search_documents(query, [store_name], top_k=top_k)