"""
Backward compatibility layer for existing elasticsearch.py functions.
"""

from typing import List, Dict, Any
from .elasticsearch_manager import ElasticsearchManager
from .documents_new import AIDocument
import logging

logger = logging.getLogger(__name__)

# Global instance for backward compatibility
_es_manager = None

def get_elasticsearch_manager() -> ElasticsearchManager:
    """Get or create global ElasticsearchManager instance"""
    global _es_manager
    if _es_manager is None:
        _es_manager = ElasticsearchManager()
    return _es_manager

def upsert_documents(docs: List[Dict[str, Any]], index_name: str, id_field: str) -> None:
    """
    DEPRECATED: Backward compatibility function for raw dict upserts.
    
    This function maintains compatibility with existing code that uses
    the old upsert_documents function. New code should use ElasticsearchManager directly.
    
    Args:
        docs: List of document dictionaries
        index_name: Name of the Elasticsearch index
        id_field: Field name to use as document ID
    """
    logger.warning("upsert_documents is deprecated. Use ElasticsearchManager directly.")
    
    if not docs:
        return
    
    # Convert raw dicts to AIDocuments
    ai_documents = []
    for doc in docs:
        doc_id = doc.get(id_field)
        
        ai_doc = AIDocument(
            page_content=doc.get('text', ''),
            metadata=doc
        )
        
        if doc_id:
            ai_doc.id = doc_id
        
        ai_documents.append(ai_doc)
    
    # Use ElasticsearchManager for actual storage
    es_manager = get_elasticsearch_manager()
    results = es_manager.upsert_documents(ai_documents, index_name)
    
    logger.info(f"Backward compatibility upsert: {results}")

# Re-export for backward compatibility
__all__ = ['upsert_documents']
