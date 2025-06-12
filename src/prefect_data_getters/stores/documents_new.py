import pprint
import logging
from langchain_core.documents import Document
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field

logger = logging.getLogger(__name__)

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
    
    def save(self, store_name: str, also_store_vectors: bool = True) -> bool:
        """
        Save this document to Elasticsearch storage.
        
        Args:
            store_name: Name of the store/index
            also_store_vectors: Whether to also store in vector index for semantic search
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store in Elasticsearch for text search and primary storage
            from .elasticsearch_manager import ElasticsearchManager
            es_manager = ElasticsearchManager()
            success = es_manager.save_document(self, store_name)
            
            # Optionally store in vector index for semantic search
            if also_store_vectors and success:
                try:
                    from .vectorstore import ESVectorStore
                    from langchain_core.documents import Document
                    
                    vector_store = ESVectorStore(store_name)
                    base_doc = Document(
                        page_content=self.page_content,
                        metadata=self.metadata,
                        id=self.get_display_id()
                    )
                    vector_store.batch_process_and_store([base_doc])
                    logger.info(f"Stored document {self.get_display_id()} in both text and vector stores")
                except Exception as e:
                    logger.warning(f"Vector storage failed for {self.get_display_id()}: {e}")
                    # Don't fail the whole operation if vector storage fails
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save document {self.get_display_id()}: {e}")
            return False

    def delete(self, store_name: str) -> bool:
        """
        Delete this document from storage.
        
        Args:
            store_name: Name of the store/index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from .elasticsearch_manager import ElasticsearchManager
            es_manager = ElasticsearchManager()
            success = es_manager.delete_document(self.get_display_id(), store_name)
            
            # Note: Vector store deletion would require additional implementation
            # Current ESVectorStore doesn't support deletion by ID
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete document {self.get_display_id()}: {e}")
            return False

    @classmethod
    def search(cls, query: str, store_name: str,
               search_type: str = "text", top_k: int = 10) -> List['AIDocument']:
        """
        Search for documents.
        
        Args:
            query: Search query string
            store_name: Name of the store/index
            search_type: "text" (Elasticsearch full-text), "vector" (semantic), or "hybrid"
            top_k: Maximum number of results
            
        Returns:
            List of AIDocument instances with search scores
        """
        from .document_registry import DocumentTypeRegistry
        document_class = DocumentTypeRegistry.get_document_class(store_name)
        
        results = []
        
        try:
            if search_type in ["text", "hybrid"]:
                # Elasticsearch text search
                from .elasticsearch_manager import ElasticsearchManager
                es_manager = ElasticsearchManager()
                
                es_query = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["page_content^2", "metadata.*"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    }
                }
                
                text_results = es_manager.search_documents(es_query, store_name, document_class, top_k)
                results.extend(text_results)
            
            if search_type in ["vector", "hybrid"]:
                # Vector semantic search
                try:
                    from .vectorstore import ESVectorStore
                    vector_store = ESVectorStore(store_name)
                    vector_results = vector_store.getESStore().similarity_search(query, k=top_k)
                    
                    # Convert to AIDocuments
                    for doc in vector_results:
                        ai_doc = document_class.from_dict({
                            'page_content': doc.page_content,
                            'metadata': doc.metadata or {},
                            'id': doc.metadata.get('id') if doc.metadata else None
                        })
                        ai_doc.search_score = getattr(doc, 'search_score', 0.0)
                        results.append(ai_doc)
                        
                except Exception as e:
                    logger.warning(f"Vector search failed for {store_name}: {e}")
            
            # Deduplicate and sort by score
            unique_results = {}
            for doc in results:
                doc_id = doc.get_display_id()
                if doc_id not in unique_results or (doc.search_score or 0) > (unique_results[doc_id].search_score or 0):
                    unique_results[doc_id] = doc
            
            final_results = list(unique_results.values())
            return sorted(final_results, key=lambda x: x.search_score or 0, reverse=True)[:top_k]
            
        except Exception as e:
            logger.error(f"Search failed for {store_name}: {e}")
            return []