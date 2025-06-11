"""
Document Type Registry for managing document type creation and registration.
"""

from typing import Dict, Type, Optional, List
from ..utilities.constants import VECTOR_STORE_NAMES

# Import will be added after Phase 1 is complete
from .documents_new import AIDocument

class DocumentTypeRegistry:
    """
    Registry pattern for document type creation and management.
    
    This class maintains a mapping between store names and their corresponding
    document classes, enabling dynamic document creation and type management.
    """
    
    _types: Dict[str, Type['AIDocument']] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, store_name: VECTOR_STORE_NAMES, document_class: Type['AIDocument']) -> None:
        """
        Register a document class for a specific store.
        
        Args:
            store_name: The name of the vector store/index
            document_class: The AIDocument subclass to use for this store
        """
        cls._types[store_name] = document_class
        print(f"Registered {document_class.__name__} for store '{store_name}'")
    
    @classmethod
    def create_document(cls, data: dict, store_name: VECTOR_STORE_NAMES) -> 'AIDocument':
        """
        Create appropriate document type based on store name.
        
        Args:
            data: Dictionary containing document data (page_content, metadata, etc.)
            store_name: The name of the vector store/index
            
        Returns:
            AIDocument instance of the appropriate subclass
            
        Raises:
            ValueError: If store_name is not registered
        """
        if not cls._initialized:
            cls._ensure_types_loaded()
        
        document_class = cls._types.get(store_name)
        if document_class is None:
            # Fallback to base AIDocument class
            from .documents_new import AIDocument
            print(f"Warning: No specific document class registered for '{store_name}', using base AIDocument")
            document_class = AIDocument
        
        return document_class.from_dict(data)
    
    @classmethod
    def get_document_class(cls, store_name: VECTOR_STORE_NAMES) -> Type['AIDocument']:
        """
        Get the document class for a store.
        
        Args:
            store_name: The name of the vector store/index
            
        Returns:
            The AIDocument subclass for this store
        """
        if not cls._initialized:
            cls._ensure_types_loaded()
        
        document_class = cls._types.get(store_name)
        if document_class is None:
            from .documents_new import AIDocument
            return AIDocument
        
        return document_class
    
    @classmethod
    def list_registered_types(cls) -> Dict[str, str]:
        """
        List all registered document types.
        
        Returns:
            Dictionary mapping store names to document class names
        """
        if not cls._initialized:
            cls._ensure_types_loaded()
        
        return {store_name: doc_class.__name__ for store_name, doc_class in cls._types.items()}
    
    @classmethod
    def is_registered(cls, store_name: VECTOR_STORE_NAMES) -> bool:
        """
        Check if a store name is registered.
        
        Args:
            store_name: The name of the vector store/index
            
        Returns:
            True if registered, False otherwise
        """
        if not cls._initialized:
            cls._ensure_types_loaded()
        
        return store_name in cls._types
    
    @classmethod
    def _ensure_types_loaded(cls) -> None:
        """
        Ensure all document types are loaded and registered.
        This method imports all document type modules to trigger registration.
        """
        if cls._initialized:
            return
        
        try:
            # Import all document type modules to trigger auto-registration
            # These imports will be added as document types are migrated
            pass
            # from .document_types.jira_document import JiraDocument
            # from .document_types.email_document import EmailDocument
            # from .document_types.slack_document import SlackMessageDocument
            # from .document_types.slab_document import SlabDocument, SlabChunkDocument
            # from .document_types.bitbucket_document import BitbucketPR
            
        except ImportError as e:
            print(f"Warning: Could not import some document types: {e}")
        
        cls._initialized = True
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear the registry (mainly for testing purposes)"""
        cls._types.clear()
        cls._initialized = False


def register_document_type(store_name: VECTOR_STORE_NAMES):
    """
    Decorator to automatically register document types.
    
    Usage:
        @register_document_type("jira_issues")
        class JiraDocument(AIDocument):
            pass
    
    Args:
        store_name: The name of the vector store/index this document type handles
    """
    def decorator(cls: Type['AIDocument']):
        DocumentTypeRegistry.register(store_name, cls)
        return cls
    return decorator