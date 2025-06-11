# Phase 1: Core Architecture Refactoring

## Overview

This phase focuses on the fundamental architectural changes to eliminate the wrapper pattern and establish direct inheritance from langchain's Document class.

## Goals

1. **Refactor AIDocument base class** to inherit from `langchain_core.documents.Document`
2. **Eliminate `_document` wrapper** and all pass-through methods
3. **Replace `_type_name`** with `__class__.__name__` property
4. **Add basic Elasticsearch integration methods** to the base class
5. **Maintain backward compatibility** during transition

## Current State Analysis

### Problems to Solve
- AIDocument wraps Document instead of inheriting from it
- Duplication of properties (`id`, `page_content`) between wrapper and wrapped object
- Pass-through methods like `set_page_content()` maintain synchronization
- Manual `_type_name` management when `__class__.__name__` could be used

### Current AIDocument Structure
```python
class AIDocument:
    def __init__(self, doc: Document):
        self._document = doc          # ← Wrapper pattern
        self._type_name = None        # ← Manual type tracking
        self.id = self._document.id   # ← Property duplication
        self.page_content = self._document.page_content  # ← Property duplication
        self.search_score = None
    
    def set_page_content(self, content: str) -> None:  # ← Pass-through method
        self._document.page_content = content
        self.page_content = content
```

## Implementation Plan

### Step 1: Create New AIDocument Base Class

**File**: `src/prefect_data_getters/stores/documents_new.py`

```python
import pprint
from langchain_core.documents import Document
from datetime import datetime
from typing import Optional, Dict, Any

class AIDocument(Document):
    """
    Enhanced Document class that inherits from langchain_core.documents.Document
    and adds domain-specific functionality for our application.
    """
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize AIDocument with direct inheritance from Document.
        
        Args:
            page_content: The main content of the document
            metadata: Dictionary of metadata associated with the document
            **kwargs: Additional arguments passed to parent Document class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
        self.search_score: Optional[float] = None
    
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
        doc = cls(
            page_content=data.get('page_content', ''),
            metadata=data.get('metadata', {})
        )
        if 'id' in data and data['id']:
            doc.id = data['id']
        return doc
```

### Step 2: Create Backward Compatibility Layer

**File**: `src/prefect_data_getters/stores/compatibility.py`

```python
"""
Backward compatibility layer to ease migration from old AIDocument to new one.
This file should be removed after migration is complete.
"""

from langchain_core.documents import Document
from .documents_new import AIDocument as NewAIDocument
from .documents import AIDocument as OldAIDocument
from ..utilities.constants import VECTOR_STORE_NAMES

class DocumentMigrationHelper:
    """Helper class to migrate between old and new document formats"""
    
    @staticmethod
    def convert_old_to_new(old_doc: OldAIDocument) -> NewAIDocument:
        """Convert old AIDocument to new AIDocument"""
        new_doc = NewAIDocument(
            page_content=old_doc.page_content,
            metadata=old_doc._document.metadata or {}
        )
        new_doc.search_score = old_doc.search_score
        if hasattr(old_doc, 'id') and old_doc.id:
            new_doc.id = old_doc.id
        return new_doc
    
    @staticmethod
    def convert_document_to_new(doc: Document) -> NewAIDocument:
        """Convert base Document to new AIDocument"""
        new_doc = NewAIDocument(
            page_content=doc.page_content,
            metadata=doc.metadata or {}
        )
        if hasattr(doc, 'id') and doc.id:
            new_doc.id = doc.id
        return new_doc
    
    @staticmethod
    def batch_convert_documents(docs: list[Document]) -> list[NewAIDocument]:
        """Convert a list of Documents to new AIDocuments"""
        return [DocumentMigrationHelper.convert_document_to_new(doc) for doc in docs]
```

### Step 3: Create Basic Tests

**File**: `src/prefect_data_getters/test/test_phase1_refactoring.py`

```python
import pytest
from ..stores.documents_new import AIDocument
from ..stores.compatibility import DocumentMigrationHelper
from langchain_core.documents import Document

class TestPhase1Refactoring:
    """Test suite for Phase 1 refactoring changes"""
    
    def test_aidocument_inheritance(self):
        """Test that new AIDocument properly inherits from Document"""
        doc = AIDocument("test content", {"key": "value"})
        
        # Test inheritance
        assert isinstance(doc, Document)
        
        # Test properties
        assert doc.page_content == "test content"
        assert doc.metadata["key"] == "value"
        assert doc.document_type == "AIDocument"
    
    def test_document_type_property(self):
        """Test that document_type uses class name"""
        doc = AIDocument("content")
        assert doc.document_type == "AIDocument"
        
        # Test with subclass
        class TestDocument(AIDocument):
            pass
        
        test_doc = TestDocument("content")
        assert test_doc.document_type == "TestDocument"
    
    def test_get_display_id(self):
        """Test display ID functionality"""
        # Test without ID
        doc = AIDocument("content")
        assert doc.get_display_id() == "Unknown"
        
        # Test with ID
        doc.id = "test-123"
        assert doc.get_display_id() == "test-123"
    
    def test_metadata_helper(self):
        """Test metadata helper method"""
        metadata = {"key1": "value1", "key2": None}
        doc = AIDocument("content", metadata)
        
        assert doc._get_metadata("key1") == "value1"
        assert doc._get_metadata("key2") is None
        assert doc._get_metadata("nonexistent") is None
        assert doc._get_metadata("nonexistent", "default") == "default"
    
    def test_to_dict_from_dict(self):
        """Test serialization methods"""
        original_doc = AIDocument("test content", {"key": "value"})
        original_doc.id = "test-123"
        
        # Convert to dict
        doc_dict = original_doc.to_dict()
        expected_dict = {
            'id': 'test-123',
            'page_content': 'test content',
            'metadata': {'key': 'value'},
            'document_type': 'AIDocument'
        }
        assert doc_dict == expected_dict
        
        # Convert back from dict
        restored_doc = AIDocument.from_dict(doc_dict)
        assert restored_doc.page_content == original_doc.page_content
        assert restored_doc.metadata == original_doc.metadata
        assert restored_doc.id == original_doc.id
    
    def test_compatibility_conversion(self):
        """Test backward compatibility conversion"""
        # Create base Document
        base_doc = Document("test content", {"key": "value"})
        base_doc.id = "test-123"
        
        # Convert to new AIDocument
        ai_doc = DocumentMigrationHelper.convert_document_to_new(base_doc)
        
        assert isinstance(ai_doc, AIDocument)
        assert ai_doc.page_content == "test content"
        assert ai_doc.metadata["key"] == "value"
        assert ai_doc.id == "test-123"
    
    def test_format_document_string(self):
        """Test document string formatting"""
        doc = AIDocument("test content", {"key": "value"})
        doc.id = "test-123"
        
        formatted = doc._format_document_string({"Test Field": "test value"})
        
        assert "Document Type: AIDocument" in formatted
        assert "Test Field: test value" in formatted
        assert "test content" in formatted
        assert "END: test-123" in formatted
```

## Migration Steps

### Step 1: Implementation
1. Create `documents_new.py` with new AIDocument class
2. Create `compatibility.py` with migration helpers
3. Create test file and run tests

### Step 2: Validation
1. Run existing tests to ensure no breakage
2. Test compatibility layer with existing code
3. Verify all functionality works as expected

### Step 3: Gradual Migration
1. Update one consumer at a time to use new AIDocument
2. Use compatibility layer during transition
3. Monitor for any issues

## Success Criteria

- [ ] New AIDocument inherits directly from Document
- [ ] No `_document` wrapper or pass-through methods
- [ ] `document_type` property uses `__class__.__name__`
- [ ] All existing functionality preserved
- [ ] Backward compatibility layer works
- [ ] All tests pass
- [ ] No breaking changes to existing consumers

## Files Modified/Created

### New Files
- `src/prefect_data_getters/stores/documents_new.py`
- `src/prefect_data_getters/stores/compatibility.py`
- `src/prefect_data_getters/test/test_phase1_refactoring.py`

### Files to Update Later
- `src/prefect_data_getters/stores/documents.py` (in later phase)
- All consumer files (in later phases)

## Next Phase

After Phase 1 is complete and validated, proceed to **Phase 2: Document Type Registry** which will implement the registry pattern for managing different document types.

## Rollback Plan

If issues arise:
1. Keep old `documents.py` unchanged during Phase 1
2. Use compatibility layer to isolate changes
3. Can easily revert by removing new files
4. No existing functionality is modified in this phase