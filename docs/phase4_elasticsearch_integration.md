# Phase 4: Elasticsearch Integration

## Overview

This phase implements the unified storage layer that integrates Elasticsearch operations directly into the document classes, replacing the separate `upsert_documents` function and providing a cohesive storage interface.

## Goals

1. **Create ElasticsearchManager** for centralized ES operations
2. **Implement UnifiedDocumentStore** as the main storage interface
3. **Replace raw `upsert_documents` function** with document-aware methods
4. **Integrate storage operations** into AIDocument classes
5. **Provide unified search interface** across text and vector stores
6. **Maintain backward compatibility** during transition

## Prerequisites

- Phase 1 must be completed (new AIDocument base class)
- Phase 2 must be completed (document registry)
- Phase 3 must be completed (document types refactoring)
- All previous phase tests must be passing

## Current State Analysis

### Problems to Solve
- Separate `upsert_documents` function works with raw dicts
- No integration between document classes and storage
- Manual coordination between Elasticsearch and vector stores
- Limited error handling and retry logic
- No unified search interface

### Current Storage Pattern
```python
# Current approach - separate and manual
def upsert_documents(docs: list[dict], index_name: str, id_field: str):
    # Raw dict operations, no document awareness
    
# Usage scattered across codebase
upsert_documents([processed], "email_messages_llm_processed", "google-id")
```

## Implementation Plan

### Step 1: Create Elasticsearch Manager

**File**: `src/prefect_data_getters/stores/elasticsearch_manager.py`

```python
"""
Elasticsearch Manager for centralized document storage operations.
"""

from typing import List, Optional, Type, Dict, Any, Union
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError, ConnectionError
import logging
from ..utilities.constants import ES_URL
from .documents_new import AIDocument

logger = logging.getLogger(__name__)

class ElasticsearchManager:
    """
    Centralized Elasticsearch operations for AIDocuments.
    
    This class provides a high-level interface for storing, retrieving,
    and searching AIDocument instances in Elasticsearch.
    """
    
    def __init__(self, es_client: Optional[Elasticsearch] = None, max_retries: int = 3):
        """
        Initialize ElasticsearchManager.
        
        Args:
            es_client: Optional Elasticsearch client instance
            max_retries: Maximum number of retry attempts for failed operations
        """
        self.es = es_client or Elasticsearch(ES_URL)
        self.max_retries = max_retries
    
    def save_document(self, document: AIDocument, index_name: str) -> bool:
        """
        Save a single document to Elasticsearch.
        
        Args:
            document: AIDocument instance to save
            index_name: Name of the Elasticsearch index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_dict = document.to_dict()
            response = self.es.index(
                index=index_name,
                id=document.get_display_id(),
                body=doc_dict
            )
            logger.info(f"Saved document {document.get_display_id()} to index {index_name}")
            return response.get('result') in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"Error saving document {document.get_display_id()}: {e}")
            return False
    
    def save_documents(self, documents: List[AIDocument], index_name: str) -> Dict[str, int]:
        """
        Save multiple documents using bulk API.
        
        Args:
            documents: List of AIDocument instances to save
            index_name: Name of the Elasticsearch index
            
        Returns:
            Dictionary with success/failure counts
        """
        if not documents:
            return {'success': 0, 'failed': 0}
        
        actions = []
        for doc in documents:
            action = {
                "_op_type": "index",
                "_index": index_name,
                "_id": doc.get_display_id(),
                "_source": doc.to_dict()
            }
            actions.append(action)
        
        try:
            success_count, failed_items = helpers.bulk(
                self.es, 
                actions,
                max_retries=self.max_retries,
                initial_backoff=2,
                max_backoff=600
            )
            
            failed_count = len(failed_items) if failed_items else 0
            logger.info(f"Bulk save to {index_name}: {success_count} success, {failed_count} failed")
            
            return {'success': success_count, 'failed': failed_count}
            
        except Exception as e:
            logger.error(f"Error in bulk save to {index_name}: {e}")
            return {'success': 0, 'failed': len(documents)}
    
    def upsert_documents(self, documents: List[AIDocument], index_name: str) -> Dict[str, int]:
        """
        Upsert multiple documents using bulk API.
        
        Args:
            documents: List of AIDocument instances to upsert
            index_name: Name of the Elasticsearch index
            
        Returns:
            Dictionary with success/failure counts
        """
        if not documents:
            return {'success': 0, 'failed': 0}
        
        actions = []
        for doc in documents:
            action = {
                "_op_type": "update",
                "_index": index_name,
                "_id": doc.get_display_id(),
                "doc": doc.to_dict(),
                "doc_as_upsert": True
            }
            actions.append(action)
        
        try:
            success_count, failed_items = helpers.bulk(
                self.es,
                actions,
                max_retries=self.max_retries,
                initial_backoff=2,
                max_backoff=600
            )
            
            failed_count = len(failed_items) if failed_items else 0
            logger.info(f"Bulk upsert to {index_name}: {success_count} success, {failed_count} failed")
            
            return {'success': success_count, 'failed': failed_count}
            
        except Exception as e:
            logger.error(f"Error in bulk upsert to {index_name}: {e}")
            return {'success': 0, 'failed': len(documents)}
    
    def load_document(self, doc_id: str, index_name: str, 
                     document_class: Type[AIDocument] = AIDocument) -> Optional[AIDocument]:
        """
        Load a document by ID.
        
        Args:
            doc_id: Document ID to load
            index_name: Name of the Elasticsearch index
            document_class: AIDocument subclass to instantiate
            
        Returns:
            AIDocument instance or None if not found
        """
        try:
            response = self.es.get(index=index_name, id=doc_id)
            doc = document_class.from_dict(response['_source'])
            logger.debug(f"Loaded document {doc_id} from index {index_name}")
            return doc
            
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found in index {index_name}")
            return None
        except Exception as e:
            logger.error(f"Error loading document {doc_id}: {e}")
            return None
    
    def search_documents(self, query: dict, index_name: str,
                        document_class: Type[AIDocument] = AIDocument,
                        size: int = 10) -> List[AIDocument]:
        """
        Search documents and return as AIDocument instances.
        
        Args:
            query: Elasticsearch query DSL
            index_name: Name of the Elasticsearch index
            document_class: AIDocument subclass to instantiate
            size: Maximum number of results to return
            
        Returns:
            List of AIDocument instances with search scores
        """
        try:
            query['size'] = size
            response = self.es.search(index=index_name, body=query)
            
            documents = []
            for hit in response['hits']['hits']:
                doc = document_class.from_dict(hit['_source'])
                doc.search_score = hit['_score']
                documents.append(doc)
            
            logger.debug(f"Search in {index_name} returned {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error searching in {index_name}: {e}")
            return []
    
    def delete_document(self, doc_id: str, index_name: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID to delete
            index_name: Name of the Elasticsearch index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.es.delete(index=index_name, id=doc_id)
            logger.info(f"Deleted document {doc_id} from index {index_name}")
            return response.get('result') == 'deleted'
            
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found for deletion in index {index_name}")
            return False
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    def index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists.
        
        Args:
            index_name: Name of the Elasticsearch index
            
        Returns:
            True if index exists, False otherwise
        """
        try:
            return self.es.indices.exists(index=index_name)
        except Exception as e:
            logger.error(f"Error checking if index {index_name} exists: {e}")
            return False
    
    def create_index(self, index_name: str, mapping: Optional[dict] = None) -> bool:
        """
        Create an index with optional mapping.
        
        Args:
            index_name: Name of the Elasticsearch index
            mapping: Optional index mapping
            
        Returns:
            True if successful, False otherwise
        """
        try:
            body = {"mappings": mapping} if mapping else {}
            response = self.es.indices.create(index=index_name, body=body)
            logger.info(f"Created index {index_name}")
            return response.get('acknowledged', False)
            
        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Elasticsearch cluster.
        
        Returns:
            Dictionary with health information
        """
        try:
            health = self.es.cluster.health()
            return {
                'status': health.get('status', 'unknown'),
                'cluster_name': health.get('cluster_name', 'unknown'),
                'number_of_nodes': health.get('number_of_nodes', 0),
                'active_shards': health.get('active_shards', 0),
                'connection': 'healthy'
            }
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return {
                'status': 'red',
                'connection': 'failed',
                'error': str(e)
            }
```

### Step 2: Create Unified Document Store

**File**: `src/prefect_data_getters/stores/unified_document_store.py`

```python
"""
Unified Document Store - Single interface for all document operations.
"""

from typing import List, Optional, Dict, Any, Union
from .elasticsearch_manager import ElasticsearchManager
from .vectorstore import ESVectorStore
from .document_registry import DocumentTypeRegistry
from .documents_new import AIDocument
from ..utilities.constants import VECTOR_STORE_NAMES
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)

class UnifiedDocumentStore:
    """
    Single interface for all document operations.
    
    This class coordinates between Elasticsearch (for full-text search and storage)
    and vector stores (for semantic search) while providing a unified API.
    """
    
    def __init__(self, es_manager: Optional[ElasticsearchManager] = None):
        """
        Initialize UnifiedDocumentStore.
        
        Args:
            es_manager: Optional ElasticsearchManager instance
        """
        self.es_manager = es_manager or ElasticsearchManager()
        self.vector_stores: Dict[str, ESVectorStore] = {}
        self.registry = DocumentTypeRegistry()
    
    def get_vector_store(self, store_name: VECTOR_STORE_NAMES) -> ESVectorStore:
        """
        Get or create vector store for given name.
        
        Args:
            store_name: Name of the vector store
            
        Returns:
            ESVectorStore instance
        """
        if store_name not in self.vector_stores:
            self.vector_stores[store_name] = ESVectorStore(store_name)
        return self.vector_stores[store_name]
    
    def store_documents(self, documents: List[AIDocument], store_name: VECTOR_STORE_NAMES,
                       store_in_vector: bool = True, store_in_elasticsearch: bool = True) -> Dict[str, Any]:
        """
        Store documents in both Elasticsearch and vector store.
        
        Args:
            documents: List of AIDocument instances to store
            store_name: Name of the store/index
            store_in_vector: Whether to store in vector store
            store_in_elasticsearch: Whether to store in Elasticsearch
            
        Returns:
            Dictionary with operation results
        """
        results = {
            'elasticsearch': {'success': 0, 'failed': 0},
            'vector_store': {'success': 0, 'failed': 0},
            'total_documents': len(documents)
        }
        
        if not documents:
            return results
        
        # Store in Elasticsearch for full-text search and primary storage
        if store_in_elasticsearch:
            try:
                es_result = self.es_manager.upsert_documents(documents, store_name)
                results['elasticsearch'] = es_result
                logger.info(f"Elasticsearch storage: {es_result}")
            except Exception as e:
                logger.error(f"Error storing in Elasticsearch: {e}")
                results['elasticsearch']['failed'] = len(documents)
        
        # Store in vector store for semantic search
        if store_in_vector:
            try:
                vector_store = self.get_vector_store(store_name)
                # Convert AIDocuments to base Documents for vector storage
                base_docs = [Document(
                    page_content=doc.page_content, 
                    metadata=doc.metadata,
                    id=doc.get_display_id()
                ) for doc in documents]
                
                vector_store.batch_process_and_store(base_docs)
                results['vector_store']['success'] = len(documents)
                logger.info(f"Vector store storage: {len(documents)} documents")
            except Exception as e:
                logger.error(f"Error storing in vector store: {e}")
                results['vector_store']['failed'] = len(documents)
        
        return results
    
    def search_documents(self, 
                        query: str, 
                        store_names: List[VECTOR_STORE_NAMES],
                        search_type: str = "hybrid",
                        top_k: int = 10,
                        filters: Optional[Dict[str, Any]] = None,
                        **kwargs) -> List[AIDocument]:
        """
        Unified search across multiple stores.
        
        Args:
            query: Search query string
            store_names: List of store names to search
            search_type: Type of search ("text", "vector", "hybrid")
            top_k: Maximum number of results to return
            filters: Optional filters to apply
            **kwargs: Additional search parameters
            
        Returns:
            List of AIDocument instances with search scores
        """
        all_results = []
        
        for store_name in store_names:
            document_class = self.registry.get_document_class(store_name)
            
            if search_type in ["text", "hybrid"]:
                # Elasticsearch full-text search
                es_query = self._build_elasticsearch_query(query, filters, top_k)
                es_results = self.es_manager.search_documents(
                    es_query, store_name, document_class, top_k
                )
                all_results.extend(es_results)
            
            if search_type in ["vector", "hybrid"]:
                # Vector similarity search
                try:
                    vector_store = self.get_vector_store(store_name)
                    vector_results = vector_store.getESStore().similarity_search(query, k=top_k)
                    
                    # Convert back to AIDocuments
                    ai_docs = []
                    for doc in vector_results:
                        ai_doc = document_class.from_dict({
                            'page_content': doc.page_content,
                            'metadata': doc.metadata or {},
                            'id': doc.metadata.get('id') if doc.metadata else None
                        })
                        ai_doc.search_score = getattr(doc, 'search_score', 0.0)
                        ai_docs.append(ai_doc)
                    
                    all_results.extend(ai_docs)
                except Exception as e:
                    logger.error(f"Error in vector search for {store_name}: {e}")
        
        # Remove duplicates and sort by score
        unique_results = self._deduplicate_results(all_results)
        return sorted(unique_results, key=lambda x: x.search_score or 0, reverse=True)[:top_k]
    
    def load_document(self, doc_id: str, store_name: VECTOR_STORE_NAMES) -> Optional[AIDocument]:
        """
        Load a document by ID from Elasticsearch.
        
        Args:
            doc_id: Document ID to load
            store_name: Name of the store/index
            
        Returns:
            AIDocument instance or None if not found
        """
        document_class = self.registry.get_document_class(store_name)
        return self.es_manager.load_document(doc_id, store_name, document_class)
    
    def delete_document(self, doc_id: str, store_name: VECTOR_STORE_NAMES) -> bool:
        """
        Delete a document from both Elasticsearch and vector store.
        
        Args:
            doc_id: Document ID to delete
            store_name: Name of the store/index
            
        Returns:
            True if successful in at least one store
        """
        es_success = self.es_manager.delete_document(doc_id, store_name)
        
        # Note: Vector store deletion would require additional implementation
        # as current ESVectorStore doesn't support deletion by ID
        
        return es_success
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all storage backends.
        
        Returns:
            Dictionary with health information for all backends
        """
        return {
            'elasticsearch': self.es_manager.health_check(),
            'vector_stores': {name: 'not_implemented' for name in self.vector_stores.keys()},
            'registry': {
                'registered_types': len(self.registry.list_registered_types()),
                'types': list(self.registry.list_registered_types().keys())
            }
        }
    
    def _build_elasticsearch_query(self, query: str, filters: Optional[Dict[str, Any]], 
                                  size: int) -> Dict[str, Any]:
        """
        Build Elasticsearch query from parameters.
        
        Args:
            query: Search query string
            filters: Optional filters to apply
            size: Maximum number of results
            
        Returns:
            Elasticsearch query dictionary
        """
        es_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["page_content^2", "metadata.*"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "size": size,
            "highlight": {
                "fields": {
                    "page_content": {"fragment_size": 150, "number_of_fragments": 3}
                }
            }
        }
        
        # Add filters if provided
        if filters:
            bool_query = {
                "bool": {
                    "must": [es_query["query"]],
                    "filter": []
                }
            }
            
            for field, value in filters.items():
                bool_query["bool"]["filter"].append({
                    "term": {f"metadata.{field}": value}
                })
            
            es_query["query"] = bool_query
        
        return es_query
    
    def _deduplicate_results(self, results: List[AIDocument]) -> List[AIDocument]:
        """
        Remove duplicate documents based on display ID.
        
        Args:
            results: List of AIDocument instances
            
        Returns:
            List of unique AIDocument instances
        """
        seen_ids = set()
        unique_results = []
        
        for doc in results:
            doc_id = doc.get_display_id()
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(doc)
        
        return unique_results
```

### Step 3: Add Storage Methods to AIDocument

**File**: Update `src/prefect_data_getters/stores/documents_new.py` (add these methods)

```python
# Add these methods to the AIDocument class

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
        from .unified_document_store import UnifiedDocumentStore
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
```

### Step 4: Create Backward Compatibility for upsert_documents

**File**: `src/prefect_data_getters/stores/elasticsearch_compatibility.py`

```python
"""
Backward compatibility layer for existing elasticsearch.py functions.
"""

from typing import List, Dict, Any
from .unified_document_store import UnifiedDocumentStore
from .documents_new import AIDocument
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
```

### Step 5: Create Phase 4 Tests

**File**: `src/prefect_data_getters/test/test_phase4_elasticsearch.py`

```python
import pytest
from unittest.mock import Mock, patch
from ..stores.elasticsearch_manager import ElasticsearchManager
from ..stores.unified_document_store import UnifiedDocumentStore
from ..stores.documents_new import AIDocument
from ..stores.elasticsearch_compatibility import upsert_documents

class TestPhase4Elasticsearch:
    """Test suite for Phase 4 Elasticsearch integration"""
    
    @pytest.fixture
    def mock_es_client(self):
        """Mock Elasticsearch client"""
        return Mock()
    
    @pytest.fixture
    def es_manager(self, mock_es_client):
        """ElasticsearchManager with mocked client"""
        return ElasticsearchManager(mock_es_client)
    
    @pytest.fixture
    def unified_store(self, es_manager):
        """UnifiedDocumentStore with mocked ES manager"""
        return UnifiedDocumentStore(es_manager)
    
    def test_elasticsearch_manager_save_document(self, es_manager, mock_es_client):
        """Test saving a single document"""
        mock_es_client.index.return_value = {'result': 'created'}
        
        doc = AIDocument("test content", {"key": "value"})
        doc.id = "test-123"
        
        result = es_manager.save_document(doc, "test_index")
        
        assert result == True
        mock_es_client.index.assert_called_once()
        call_args = mock_es_client.index.call_args
        assert call_args[1]['index'] == 'test_index'
        assert call_args[1]['id'] == 'test-123'
    
    def test_elasticsearch_manager_bulk_upsert(self, es_manager):
        """Test bulk upsert operation"""
        with patch('prefect_data_getters.stores.elasticsearch_manager.helpers.bulk') as mock_bulk:
            mock_bulk.return_value = (2, [])  # 2 successful, 0 failed
            
            docs = [
                AIDocument("content 1", {"id": "1"}),
                AIDocument("content 2", {"id": "2"})
            ]
            
            result = es_manager.upsert_documents(docs, "test_index")
            
            assert result['success'] == 2
            assert result['failed'] == 0
            mock_bulk.assert_called_once()
    
    def test_elasticsearch_manager_search(self, es_manager, mock_es_client):
        """Test document search"""
        mock_es_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_source': {
                            'page_content': 'test content',
                            'metadata': {'key': 'value'},
                            'id': 'test-123'
                        },
                        '_score': 0.95
                    }
                ]
            }
        }
        
        query = {"query": {"match": {"page_content": "test"}}}
        results = es_manager.search_documents(query, "test_index", AIDocument)
        
        assert len(results) == 1
        assert results[0].page_content == "test content"
        assert results[0].search_score == 0.95
    
    def test_unified_store_storage(self, unified_store):
        """Test unified document storage"""
        with patch.object(unified_store.es_manager, 'upsert_documents') as mock_upsert:
            mock_upsert.return_value = {'success': 1, 'failed': 0}
            
            with patch.object(unified_store, 'get_vector_store') as mock_get_vs:
                mock_vector_store = Mock()
                mock_get_vs.return_value = mock_vector_store
                
                doc = AIDocument("test content", {"key": "value"})
                results = unified_store.store_documents([doc], "test_store")
                
                assert results['elasticsearch']['success'] == 1
                mock_upsert.assert_called_once_with([doc], "test_store")
                mock_vector_store.batch_process_and_store.assert_called_once()
    
    def test_unified_store_search_hybrid(self, unified_store):
        """Test hybrid search functionality"""
        # Mock Elasticsearch search
        with patch.object(unified_store.es_manager, 'search_documents') as mock_es_search:
            mock_es_search.return_value = [AIDocument("es result", {"source": "elasticsearch"})]
            
            # Mock vector search
            with patch.object(unified_store, 'get_vector_store') as mock_get_vs:
                mock_vector_store = Mock()
                mock_langchain_doc = Mock()
                mock_langchain_doc.page_content = "vector result"
                mock_langchain_doc.metadata = {"source": "vector"}
                mock_vector_store.getESStore.return_value.similarity_search.return_value = [mock_langchain_doc]
                mock_get_vs.return_value = mock_vector_store
                
                results = unified_store.search_documents(
                    "test query", 
                    ["test_store"], 
                    search_type="hybrid"
                )
                
                assert len(results) >= 1  # Should have results from both sources
                mock_es_search.assert_called_once()
                mock_vector_store.getESStore.return_value.similarity_search.assert_called_once()
    
    def test_document_save_method(self):
        """Test AIDocument save method"""
        with patch('prefect_data_getters.stores.documents_new.UnifiedDocumentStore') as mock_store_class:
            mock_store = Mock()
            mock_store.store_documents.return_value = {'elasticsearch': {'success': 1, 'failed': 0}}
            mock_store_class.return_value = mock_store
            
            doc = AIDocument("test content", {"key": "