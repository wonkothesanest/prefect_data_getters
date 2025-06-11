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

## API Reference

### DocumentTypeRegistry

The central registry for managing document types:

```python
from prefect_data_getters.stores.document_registry import DocumentTypeRegistry

# Register a document type
DocumentTypeRegistry.register("store_name", DocumentClass)

# Create a document
doc = DocumentTypeRegistry.create_document(data_dict, "store_name")

# Check if registered
is_registered = DocumentTypeRegistry.is_registered("store_name")

# Get document class
doc_class = DocumentTypeRegistry.get_document_class("store_name")

# List all registered types
types = DocumentTypeRegistry.list_registered_types()
```

### Registration Decorator

Auto-register document types using the decorator:

```python
from prefect_data_getters.stores.document_registry import register_document_type

@register_document_type("jira_issues")
class JiraDocument(AIDocument):
    def get_display_id(self):
        return self.metadata.get('key', 'unknown')
```

### Compatibility Functions

For backward compatibility during migration:

```python
from prefect_data_getters.stores.factory_compatibility import (
    create_document_from_langchain,
    convert_documents_to_ai_documents_registry
)

# Single document
ai_doc = create_document_from_langchain(langchain_doc, "store_name")

# Multiple documents
ai_docs = convert_documents_to_ai_documents_registry(langchain_docs, "store_name")
```

## Examples

### Example 1: Registering a New Document Type

```python
from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.document_registry import register_document_type

@register_document_type("custom_documents")
class CustomDocument(AIDocument):
    def get_display_id(self):
        return f"custom-{self.metadata.get('id', 'unknown')}"
    
    def custom_method(self):
        return f"Processing {self.document_type}"
```

### Example 2: Using the Registry

```python
from prefect_data_getters.stores.document_registry import DocumentTypeRegistry

# Create document data
data = {
    'page_content': 'This is the document content',
    'metadata': {'id': '123', 'title': 'Test Document'},
    'id': 'doc-123'
}

# Create document using registry
doc = DocumentTypeRegistry.create_document(data, "custom_documents")
print(f"Created: {doc.get_display_id()}")  # Output: custom-123
```

### Example 3: Compatibility Layer Usage

```python
from langchain_core.documents import Document
from prefect_data_getters.stores.factory_compatibility import create_document_from_langchain

# Existing langchain document
langchain_doc = Document("content", {"key": "value"})

# Convert using compatibility layer
ai_doc = create_document_from_langchain(langchain_doc, "jira_issues")
```

## Error Handling

### Unregistered Document Types

If you try to create a document for an unregistered store, the registry will:
1. Print a warning message
2. Fall back to the base `AIDocument` class
3. Create the document successfully

```python
# This will work even if "unknown_store" isn't registered
doc = DocumentTypeRegistry.create_document(data, "unknown_store")
# Warning: No specific document class registered for 'unknown_store', using base AIDocument
```

### Missing Data Fields

The registry handles missing or incomplete data gracefully:

```python
# Minimal data
data = {'page_content': 'content only'}
doc = DocumentTypeRegistry.create_document(data, "store_name")
# Will have empty metadata and None id
```

## Testing

### Testing Document Registration

```python
def test_document_registration():
    @register_document_type("test_store")
    class TestDoc(AIDocument):
        pass
    
    assert DocumentTypeRegistry.is_registered("test_store")
    assert DocumentTypeRegistry.get_document_class("test_store") == TestDoc
```

### Testing Document Creation

```python
def test_document_creation():
    @register_document_type("test_store")
    class TestDoc(AIDocument):
        def get_display_id(self):
            return "test-id"
    
    data = {'page_content': 'test', 'metadata': {'key': 'value'}}
    doc = DocumentTypeRegistry.create_document(data, "test_store")
    
    assert isinstance(doc, TestDoc)
    assert doc.page_content == 'test'
    assert doc.get_display_id() == 'test-id'
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure to import the registry before using it
2. **Registration Not Working**: Ensure the decorator is applied before the class
3. **Type Not Found**: Check that the store name matches exactly
4. **Circular Imports**: Import the registry module, not individual classes

### Debug Commands

```python
# List all registered types
print(DocumentTypeRegistry.list_registered_types())

# Check if a type is registered
print(DocumentTypeRegistry.is_registered("your_store"))

# Get the class for a store
print(DocumentTypeRegistry.get_document_class("your_store"))
```

## Next Steps

After Phase 2 is complete:
1. Phase 3 will migrate individual document types to use the new base class
2. Document types will be registered using the decorator
3. The registry will be populated with all document types
4. Phase 4 will integrate with Elasticsearch using the registry

## Files Created in Phase 2

- `src/prefect_data_getters/stores/document_registry.py` - Main registry implementation
- `src/prefect_data_getters/stores/factory_compatibility.py` - Backward compatibility layer
- `src/prefect_data_getters/test/test_phase2_registry.py` - Comprehensive tests
- `docs/phase2_migration_guide.md` - This migration guide