# Plan: Remove Unified Document Store Architecture

## 🎯 Problem Analysis

### Current Issues
The `UnifiedDocumentStore` creates unnecessary complexity by trying to coordinate between "Elasticsearch" and "vector stores" when they're actually the same underlying store:

- **53 references** to `UnifiedDocumentStore` across the codebase
- **`ESVectorStore`** uses `ElasticsearchStore` under the hood - they're the same store!
- **Redundant storage paths**: storing the same data twice in the same underlying Elasticsearch cluster
- **Unnecessary complexity**: coordination logic between stores that are one and the same
- **Performance overhead**: double storage operations for the same data

### Architecture Insight
```
Current (Wrong):
📄 AIDocument → UnifiedDocumentStore → ElasticsearchManager + ESVectorStore
                                      ↓                    ↓
                                  Elasticsearch    ElasticsearchStore
                                      ↓                    ↓
                                 Same ES Cluster ← Same ES Cluster

Simplified (Correct):
📄 AIDocument → ElasticsearchManager (text queries)
             → ESVectorStore (semantic/vector queries)
                       ↓
                  Same ES Cluster
```

## 🗺️ Implementation Plan

### Phase 1: Update AIDocument Methods
**Goal**: Replace `UnifiedDocumentStore` usage with direct store access

#### Task 1.1: Update AIDocument Storage Methods

**File**: [`src/prefect_data_getters/stores/documents_new.py`](src/prefect_data_getters/stores/documents_new.py)

**Current Methods to Replace:**
- [ ] `save()` method (lines 124-140)
- [ ] `delete()` method (lines 142-157) 
- [ ] `search()` class method (lines 159-178)

**New Implementation:**

```python
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

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
```

### Phase 2: Update Compatibility Layer

#### Task 2.1: Update Elasticsearch Compatibility

**File**: [`src/prefect_data_getters/stores/elasticsearch_compatibility.py`](src/prefect_data_getters/stores/elasticsearch_compatibility.py)

**Changes Required:**
- [ ] Replace `UnifiedDocumentStore` import with `ElasticsearchManager`
- [ ] Update `get_unified_store()` to `get_elasticsearch_manager()`
- [ ] Simplify `upsert_documents()` function

**New Implementation:**

```python
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
            page_content=doc.get('page_content', ''),
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
```

### Phase 3: Update Tests

#### Task 3.1: Update Phase 4 Tests

**File**: [`src/prefect_data_getters/test/test_phase4_elasticsearch.py`](src/prefect_data_getters/test/test_phase4_elasticsearch.py)

**Changes Required:**
- [ ] Remove all `UnifiedDocumentStore` test fixtures and methods
- [ ] Add tests for direct `AIDocument` method usage
- [ ] Update compatibility layer tests

**Key Test Updates:**
```python
# Replace unified store tests with direct AIDocument tests
def test_aidocument_save_method():
    """Test AIDocument save method with direct ElasticsearchManager"""
    with patch('prefect_data_getters.stores.documents_new.ElasticsearchManager') as mock_manager_class:
        mock_es = Mock()
        mock_es.save_document.return_value = True
        mock_manager_class.return_value = mock_es
        
        doc = AIDocument("test content", {"key": "value"})
        doc.id = "test-123"
        result = doc.save("test_store")
        
        assert result == True
        mock_es.save_document.assert_called_once_with(doc, "test_store")

def test_aidocument_search_method():
    """Test AIDocument search with different search types"""
    with patch('prefect_data_getters.stores.documents_new.ElasticsearchManager') as mock_manager_class:
        mock_es = Mock()
        mock_doc = AIDocument("result", {"source": "test"})
        mock_doc.search_score = 0.9
        mock_es.search_documents.return_value = [mock_doc]
        mock_manager_class.return_value = mock_es
        
        # Test text search
        results = AIDocument.search("test query", "test_store", search_type="text")
        
        assert len(results) == 1
        assert results[0].page_content == "result"
        mock_es.search_documents.assert_called_once()
```

#### Task 3.2: Update Validation Scripts

**File**: [`src/prefect_data_getters/test/validate_phase4.py`](src/prefect_data_getters/test/validate_phase4.py)

**Changes Required:**
- [ ] Remove `UnifiedDocumentStore` import and tests
- [ ] Add validation for direct store usage
- [ ] Update success criteria

**File**: [`src/prefect_data_getters/test/demo_phase4.py`](src/prefect_data_getters/test/demo_phase4.py)

**Changes Required:**
- [ ] Remove `UnifiedDocumentStore` examples
- [ ] Add examples showing direct `AIDocument` method usage

### Phase 4: Remove UnifiedDocumentStore

#### Task 4.1: Remove Files

**Files to Delete:**
- [ ] [`src/prefect_data_getters/stores/unified_document_store.py`](src/prefect_data_getters/stores/unified_document_store.py)

#### Task 4.2: Remove Imports

**Files to Update (Remove UnifiedDocumentStore imports):**
- [ ] Update any remaining imports across the codebase
- [ ] Use search to find any missed references: `grep -r "UnifiedDocumentStore" src/`

### Phase 5: Update Documentation

#### Task 5.1: Update Architecture Documentation

**File**: [`docs/phase4_elasticsearch_integration.md`](docs/phase4_elasticsearch_integration.md)

**Changes Required:**
- [ ] Remove `UnifiedDocumentStore` references
- [ ] Update architecture diagrams
- [ ] Add documentation for direct store usage patterns

#### Task 5.2: Create Migration Guide

**New File**: `docs/unified_store_removal_migration.md`

**Content to Include:**
- [ ] Before/after comparison
- [ ] Migration steps for existing code
- [ ] New usage patterns

## 🚀 Benefits of This Approach

### Simplification
- **Removes 53 references** to `UnifiedDocumentStore`
- **Eliminates coordination logic** between stores that are the same
- **Direct store access** - no unnecessary abstraction layer
- **Leverages existing `DocumentTypeRegistry`** - no new manager classes needed

### Performance
- **No double storage** of the same data in the same ES cluster
- **Faster operations** - direct store access without coordination overhead
- **Reduced memory usage** - no coordination state to maintain

### Maintainability
- **Clearer code paths** - obvious which store is being used for what purpose
- **Easier debugging** - direct relationship between operation and store
- **Better separation of concerns** - text search vs vector search is explicit

### Flexibility
- **Optional vector storage** - can choose text-only for better performance
- **Explicit search types** - clear choice between text, vector, or hybrid search
- **Simpler testing** - direct dependencies instead of complex coordination

## ✅ Implementation Checklist

### Phase 1: AIDocument Methods
- [ ] **1.1** Replace `save()` method in `documents_new.py`
- [ ] **1.2** Replace `delete()` method in `documents_new.py`  
- [ ] **1.3** Replace `search()` method in `documents_new.py`
- [ ] **1.4** Add logging and error handling
- [ ] **1.5** Test new methods work correctly

### Phase 2: Compatibility Layer
- [ ] **2.1** Update `elasticsearch_compatibility.py`
- [ ] **2.2** Replace `UnifiedDocumentStore` with `ElasticsearchManager`
- [ ] **2.3** Test backward compatibility maintained
- [ ] **2.4** Verify `upsert_documents` still works

### Phase 3: Tests
- [ ] **3.1** Update `test_phase4_elasticsearch.py`
- [ ] **3.2** Remove `UnifiedDocumentStore` test fixtures
- [ ] **3.3** Add direct `AIDocument` method tests
- [ ] **3.4** Update `validate_phase4.py`
- [ ] **3.5** Update `demo_phase4.py`
- [ ] **3.6** Verify all tests pass

### Phase 4: Cleanup
- [ ] **4.1** Delete `unified_document_store.py`
- [ ] **4.2** Search and remove any remaining imports
- [ ] **4.3** Verify no broken references

### Phase 5: Documentation
- [ ] **5.1** Update `phase4_elasticsearch_integration.md`
- [ ] **5.2** Create migration guide
- [ ] **5.3** Update architecture diagrams
- [ ] **5.4** Document new usage patterns

## 🎯 Success Criteria

- [ ] All 53 `UnifiedDocumentStore` references removed
- [ ] `AIDocument` methods work with direct store access
- [ ] Backward compatibility maintained for `upsert_documents`
- [ ] All tests pass with new architecture
- [ ] Performance improved (no redundant storage operations)
- [ ] Code is simpler and more maintainable
- [ ] No new manager classes added (leverages existing `DocumentTypeRegistry`)

## 🔄 Migration Examples

### Before (Using UnifiedDocumentStore)
```python
from prefect_data_getters.stores.unified_document_store import UnifiedDocumentStore

# Old way - complex coordination
store = UnifiedDocumentStore()
results = store.store_documents([doc], "my_store", store_in_vector=True, store_in_elasticsearch=True)

# Old search - complex API
results = store.search_documents("query", ["my_store"], search_type="hybrid")
```

### After (Direct Store Access)
```python
# New way - simple and direct
doc = AIDocument("content", {"key": "value"})

# Simple save with optional vector storage
success = doc.save("my_store", also_store_vectors=True)

# Simple search with explicit type
results = AIDocument.search("query", "my_store", search_type="hybrid")
```

## 📋 Notes

1. **Keep `DocumentTypeRegistry`** - it serves a different purpose (document type management)
2. **No new manager classes** - direct store instantiation is simpler
3. **Maintain all functionality** - just remove the unnecessary coordination layer
4. **Backward compatibility** - `upsert_documents` continues to work
5. **Performance gain** - eliminate redundant storage to same ES cluster

This plan eliminates the architectural problem while maintaining all functionality and improving both performance and code maintainability.