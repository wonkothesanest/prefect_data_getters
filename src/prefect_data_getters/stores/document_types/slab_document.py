"""
Slab document type implementations.
"""

from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.document_registry import register_document_type
import uuid

@register_document_type("slab_documents")
class SlabDocument(AIDocument):
    """Document type for Slab documents with Slab-specific functionality."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize SlabDocument.
        
        Args:
            page_content: The main content of the Slab document
            metadata: Dictionary containing Slab document metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
    
    def get_display_id(self) -> str:
        """Override to use document ID as display ID"""
        return self.document_id or "Unknown"
    
    # Slab-specific properties
    @property
    def document_id(self) -> str:
        """Get the Slab document ID"""
        return self._get_metadata("document_id", "")
    
    @property
    def title(self) -> str:
        """Get the Slab document title"""
        return self._get_metadata("title", "")
    
    @property
    def owner(self) -> str:
        """Get the Slab document owner"""
        return self._get_metadata("owner", "")
    
    @property
    def contributors(self) -> str:
        """Get the Slab document contributors"""
        return self._get_metadata("contributors", "")
    
    @property
    def topics(self) -> str:
        """Get the Slab document topics/tags"""
        return self._get_metadata("topics", "")
    
    @property
    def doc_type(self) -> str:
        """Get the Slab document type"""
        return self._get_metadata("type", "slab_document")
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "Document ID": self.document_id,
            "Title": self.title,
            "Type": self.doc_type,
            "Owner": self.owner,
            "Contributors": self.contributors,
            "Topics": self.topics
        })

@register_document_type("slab_document_chunks")
class SlabChunkDocument(SlabDocument):
    """Document type for Slab document chunks."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize SlabChunkDocument.
        
        Args:
            page_content: The main content of the Slab document chunk
            metadata: Dictionary containing Slab document metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
        
        # Generate unique ID for chunk if not provided
        if not hasattr(self, 'id') or not self.id:
            self.id = str(uuid.uuid4())
    
    def get_display_id(self) -> str:
        """Override to use generated UUID as display ID"""
        return getattr(self, 'id', str(uuid.uuid4()))
    
    @property
    def doc_type(self) -> str:
        """Get the document type (overridden for chunks)"""
        return self._get_metadata("type", "slab_chunk")
    
    @property
    def parent_document_id(self) -> str:
        """Get the parent document ID this chunk belongs to"""
        return self.document_id
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "Chunk ID": self.get_display_id(),
            "Parent Document ID": self.parent_document_id,
            "Title": self.title,
            "Type": self.doc_type,
            "Owner": self.owner,
            "Contributors": self.contributors,
            "Topics": self.topics
        })