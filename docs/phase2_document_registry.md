# Phase 2: Document Type Registry

## Overview

This phase implements a registry pattern to manage different document types and their creation, eliminating the need for the large factory function and making it easier to add new document types.

## Goals

1. **Create DocumentTypeRegistry** for centralized document type management
2. **Implement auto-registration decorator** for easy document type registration
3. **Replace factory functions** with registry-based creation
4. **Simplify document type creation** and management
5. **Maintain backward compatibility** with existing factory functions

## Prerequisites

- Phase 1 must be completed (new AIDocument base class)
- All Phase 1 tests must be passing

## Current State Analysis

### Problems to Solve
- Large factory function with hardcoded type mapping
- Manual maintenance of document type mappings
- Difficult to add new document types
- No centralized registry of available document types

### Current Factory Function
```python
def _create_document(doc: Document, name: VECTOR_STORE_NAMES) -> AIDocument:
    """Factory function to create a document instance based on the vector store name."""
    if name == "jira_issues":
        return JiraDocument(doc)
    elif name == "email_messages":
        return EmailDocument(doc)
    elif name == "slack_messages":
        return SlackMessageDocument(doc)
    # ... more hardcoded mappings
    else:
        raise ValueError(f"Unknown document type: {name}")
```

## Implementation Plan

### Step 1: Create Document Registry

**File**: `src/prefect_data_getters/stores/document_registry.py`

```python
"""
Document Type Registry for managing document type creation and registration.
"""

from typing import Dict, Type, Optional, List
from ..utilities.constants import VECTOR_STORE_NAMES

# Import will be added after Phase 1 is complete
# from .documents_new import AIDocument

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
```

### Step 2: Create Compatibility Layer for Factory Functions

**File**: `src/prefect_data_getters/stores/factory_compatibility.py`

```python
"""
Compatibility layer for existing factory functions.
This maintains backward compatibility while transitioning to the registry pattern.
"""

from typing import List
from langchain_core.documents import Document
from .document_registry import DocumentTypeRegistry
from ..utilities.constants import VECTOR_STORE_NAMES

# Import will be added after Phase 1 is complete
# from .documents_new import AIDocument

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
```

### Step 3: Create Registry Tests

**File**: `src/prefect_data_getters/test/test_phase2_registry.py`

```python
import pytest
from ..stores.document_registry import DocumentTypeRegistry, register_document_type
from ..stores.factory_compatibility import create_document_from_langchain, convert_documents_to_ai_documents_registry
from ..stores.documents_new import AIDocument
from langchain_core.documents import Document

class TestDocumentRegistry:
    """Test suite for Phase 2 document registry"""
    
    def setup_method(self):
        """Clear registry before each test"""
        DocumentTypeRegistry.clear_registry()
    
    def test_register_document_type(self):
        """Test manual registration of document types"""
        class TestDocument(AIDocument):
            pass
        
        DocumentTypeRegistry.register("test_store", TestDocument)
        
        assert DocumentTypeRegistry.is_registered("test_store")
        assert DocumentTypeRegistry.get_document_class("test_store") == TestDocument
    
    def test_register_decorator(self):
        """Test auto-registration decorator"""
        @register_document_type("decorated_store")
        class DecoratedDocument(AIDocument):
            pass
        
        assert DocumentTypeRegistry.is_registered("decorated_store")
        assert DocumentTypeRegistry.get_document_class("decorated_store") == DecoratedDocument
    
    def test_create_document_registered_type(self):
        """Test document creation with registered type"""
        @register_document_type("test_store")
        class TestDocument(AIDocument):
            def get_display_id(self):
                return "test-id"
        
        data = {
            'page_content': 'test content',
            'metadata': {'key': 'value'},
            'id': 'test-123'
        }
        
        doc = DocumentTypeRegistry.create_document(data, "test_store")
        
        assert isinstance(doc, TestDocument)
        assert doc.page_content == 'test content'
        assert doc.metadata['key'] == 'value'
        assert doc.id == 'test-123'
        assert doc.get_display_id() == 'test-id'
    
    def test_create_document_unregistered_type(self):
        """Test document creation with unregistered type falls back to base class"""
        data = {
            'page_content': 'test content',
            'metadata': {'key': 'value'}
        }
        
        doc = DocumentTypeRegistry.create_document(data, "unregistered_store")
        
        assert isinstance(doc, AIDocument)
        assert doc.page_content == 'test content'
        assert doc.metadata['key'] == 'value'
    
    def test_list_registered_types(self):
        """Test listing registered types"""
        @register_document_type("store1")
        class Doc1(AIDocument):
            pass
        
        @register_document_type("store2")
        class Doc2(AIDocument):
            pass
        
        types = DocumentTypeRegistry.list_registered_types()
        
        assert "store1" in types
        assert "store2" in types
        assert types["store1"] == "Doc1"
        assert types["store2"] == "Doc2"
    
    def test_factory_compatibility(self):
        """Test backward compatibility factory functions"""
        @register_document_type("test_store")
        class TestDocument(AIDocument):
            pass
        
        # Test single document creation
        langchain_doc = Document("test content", {"key": "value"})
        langchain_doc.id = "test-123"
        
        ai_doc = create_document_from_langchain(langchain_doc, "test_store")
        
        assert isinstance(ai_doc, TestDocument)
        assert ai_doc.page_content == "test content"
        assert ai_doc.metadata["key"] == "value"
        assert ai_doc.id == "test-123"
        
        # Test batch conversion
        langchain_docs = [
            Document("content1", {"id": "1"}),
            Document("content2", {"id": "2"})
        ]
        
        ai_docs = convert_documents_to_ai_documents_registry(langchain_docs, "test_store")
        
        assert len(ai_docs) == 2
        assert all(isinstance(doc, TestDocument) for doc in ai_docs)
        assert ai_docs[0].page_content == "content1"
        assert ai_docs[1].page_content == "content2"
```

### Step 4: Create Migration Guide

**File**: `docs/phase2_migration_guide.md`

```markdown
# Phase 2 Migration Guide

## Overview
This guide helps migrate from the old factory function pattern to the new registry pattern.

## Before (Old Pattern)
```python
# Old factory function
def _create_document(doc: Document, name: VECTOR_STORE_NAMES) -> AIDocument:
    if name == "jira_issues":
        return JiraDocument(doc)
    elif name == "email_messages":
        return EmailDocument(doc)
    # ... more hardcoded mappings

# Usage
ai_doc = _create_document(langchain_doc, "jira_issues")
```

## After (Registry Pattern)
```python
# Registration (done once per document type)
@register_document_type("jira_issues")
class JiraDocument(AIDocument):
    pass

# Usage
ai_doc = DocumentTypeRegistry.create_document(data_dict, "jira_issues")
# or using compatibility function
ai_doc = create_document_from_langchain(langchain_doc, "jira_issues")
```

## Migration Steps

1. **Keep old functions working** - compatibility layer maintains existing API
2. **Register document types** - add @register_document_type decorator to each document class
3. **Update consumers gradually** - replace old factory calls with new registry calls
4. **Remove old functions** - in later phase after all consumers updated

## Benefits

- **Extensible**: Easy to add new document types
- **Maintainable**: No hardcoded type mappings
- **Discoverable**: Can list all registered types
- **Type-safe**: Better IDE support and type checking
```

## Migration Steps

### Step 1: Implementation
1. Create `document_registry.py` with registry implementation
2. Create `factory_compatibility.py` with backward compatibility
3. Create test file and run tests

### Step 2: Validation
1. Run all existing tests to ensure no breakage
2. Test registry functionality with mock document types
3. Verify compatibility layer works with existing code

### Step 3: Preparation for Phase 3
1. Registry is ready to receive document type registrations
2. Compatibility layer allows gradual migration
3. All infrastructure in place for document type refactoring

## Success Criteria

- [ ] DocumentTypeRegistry class implemented and tested
- [ ] Auto-registration decorator works correctly
- [ ] Compatibility layer maintains existing factory function behavior
- [ ] All tests pass
- [ ] No breaking changes to existing consumers
- [ ] Registry can handle unregistered types gracefully

## Files Modified/Created

### New Files
- `src/prefect_data_getters/stores/document_registry.py`
- `src/prefect_data_getters/stores/factory_compatibility.py`
- `src/prefect_data_getters/test/test_phase2_registry.py`
- `docs/phase2_migration_guide.md`

### Files to Update Later
- Individual document type files (in Phase 3)
- Consumer files (in Phase 4)

## Next Phase

After Phase 2 is complete, proceed to **Phase 3: Document Type Refactoring** which will migrate individual document types to use the new base class and registry.

## Rollback Plan

If issues arise:
1. Registry is additive - doesn't modify existing code
2. Compatibility layer isolates changes
3. Can disable registry and fall back to old factory functions
4. Remove new files to completely rollback