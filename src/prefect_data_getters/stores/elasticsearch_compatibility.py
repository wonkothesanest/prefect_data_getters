"""
Backward compatibility layer for existing elasticsearch.py functions.
"""

from typing import List, Dict, Any
from prefect_data_getters.stores.unified_document_store import UnifiedDocumentStore
from prefect_data_getters.stores.documents_new import AIDocument
import logging

logger = logging.getLogger(__name__)

# Global instance for backward compatibility
_unified_store = None

def get_unified_store() -> UnifiedDocumentStore:
    """Get or create global UnifiedDocumentStore instance"""
    global _unified_store
    if _unified_store is None:
        _unified_store = UnifiedDocumentStore()
    return _unified_store

def upsert_documents(docs: List[Dict[str, Any]], index_name: str, id_field: str) -> None:
    """
    DEPRECATED: Backward compatibility function for raw dict upserts.
    
    This function maintains compatibility with existing code that uses
    the old upsert_documents function. New code should use UnifiedDocumentStore.
    
    Args:
        docs: List of document dictionaries
        index_name: Name of the Elasticsearch index
        id_field: Field name to use as document ID
    """
    logger.warning("upsert_documents is deprecated. Use UnifiedDocumentStore instead.")
    
    if not docs:
        return
    
    # Convert raw dicts to AIDocuments
    ai_documents = []
    for doc in docs:
        # Extract ID from the specified field
        doc_id = doc.get(id_field)
        
        # Create AIDocument from raw dict
        ai_doc = AIDocument(
            page_content=doc.get('page_content', ''),
            metadata=doc
        )
        
        if doc_id:
            ai_doc.id = doc_id
        
        ai_documents.append(ai_doc)
    
    # Use unified store for actual storage
    unified_store = get_unified_store()
    results = unified_store.store_documents(
        ai_documents, 
        index_name,
        store_in_vector=False,  # Only store in ES for backward compatibility
        store_in_elasticsearch=True
    )
    
    logger.info(f"Backward compatibility upsert: {results}")

# Re-export for backward compatibility
__all__ = ['upsert_documents']
