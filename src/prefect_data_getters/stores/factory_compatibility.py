"""
Compatibility layer for existing factory functions.
This maintains backward compatibility while transitioning to the registry pattern.
"""

from typing import List
from langchain_core.documents import Document
from prefect_data_getters.stores.document_registry import DocumentTypeRegistry
from prefect_data_getters.utilities.constants import VECTOR_STORE_NAMES

# Import will be added after Phase 1 is complete
from prefect_data_getters.stores.documents_new import AIDocument

def create_document_from_langchain(doc: Document, store_name: VECTOR_STORE_NAMES) -> 'AIDocument':
    """
    Create AIDocument from langchain Document using registry.
    
    This replaces the old _create_document function.
    
    Args:
        doc: langchain Document instance
        store_name: The name of the vector store/index
        
    Returns:
        AIDocument instance of the appropriate subclass
    """
    data = {
        'page_content': doc.page_content,
        'metadata': doc.metadata or {},
        'id': getattr(doc, 'id', None)
    }
    
    return DocumentTypeRegistry.create_document(data, store_name)

def convert_documents_to_ai_documents_registry(docs: List[Document], 
                                             doc_store_name: VECTOR_STORE_NAMES) -> List['AIDocument']:
    """
    Convert list of langchain Documents to AIDocuments using registry.
    
    This replaces the old convert_documents_to_ai_documents function.
    
    Args:
        docs: List of langchain Document instances
        doc_store_name: The name of the vector store/index
        
    Returns:
        List of AIDocument instances of the appropriate subclass
    """
    return [create_document_from_langchain(doc, doc_store_name) for doc in docs]

# Backward compatibility aliases (to be removed in later phase)
def _create_document(doc: Document, name: VECTOR_STORE_NAMES) -> 'AIDocument':
    """
    DEPRECATED: Use create_document_from_langchain instead.
    Maintained for backward compatibility.
    """
    print("Warning: _create_document is deprecated, use create_document_from_langchain")
    return create_document_from_langchain(doc, name)

def convert_documents_to_ai_documents(docs: List[Document], 
                                    doc_store_name: VECTOR_STORE_NAMES) -> List['AIDocument']:
    """
    DEPRECATED: Use convert_documents_to_ai_documents_registry instead.
    Maintained for backward compatibility.
    """
    print("Warning: convert_documents_to_ai_documents is deprecated, use convert_documents_to_ai_documents_registry")
    return convert_documents_to_ai_documents_registry(docs, doc_store_name)