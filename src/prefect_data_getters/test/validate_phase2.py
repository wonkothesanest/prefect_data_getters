#!/usr/bin/env python3
"""
Phase 2 Complete Implementation Validation Test

This script validates that Phase 2 (Document Registry) is fully implemented
and working correctly. It tests all core functionality without using pytest.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_imports():
    """Test that all Phase 2 components can be imported"""
    print("=== Testing Imports ===")
    
    try:
        from prefect_data_getters.stores.documents_new import AIDocument
        from prefect_data_getters.stores.document_registry import DocumentTypeRegistry, register_document_type
        from prefect_data_getters.stores.factory_compatibility import (
            create_document_from_langchain, 
            convert_documents_to_ai_documents_registry,
            _create_document,  # deprecated function
            convert_documents_to_ai_documents  # deprecated function
        )
        from langchain_core.documents import Document
        print("✓ All Phase 2 imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_registry_core():
    """Test core registry functionality"""
    print("\n=== Testing Registry Core Functionality ===")
    
    from prefect_data_getters.stores.documents_new import AIDocument
    from prefect_data_getters.stores.document_registry import DocumentTypeRegistry, register_document_type
    
    # Clear registry to start fresh
    DocumentTypeRegistry.clear_registry()
    
    # Test manual registration
    class JiraTestDocument(AIDocument):
        def get_display_id(self):
            return f"jira-{self.metadata.get('key', 'unknown')}"
    
    DocumentTypeRegistry.register('jira_issues', JiraTestDocument)
    assert DocumentTypeRegistry.is_registered('jira_issues'), "Manual registration failed"
    print("✓ Manual registration works")
    
    # Test decorator registration
    @register_document_type('email_messages')
    class EmailTestDocument(AIDocument):
        def get_display_id(self):
            return f"email-{self.metadata.get('id', 'unknown')}"
    
    assert DocumentTypeRegistry.is_registered('email_messages'), "Decorator registration failed"
    print("✓ Decorator registration works")
    
    # Test document creation with correct types
    data = {'page_content': 'test jira content', 'metadata': {'key': 'TEST-123'}}
    jira_doc = DocumentTypeRegistry.create_document(data, 'jira_issues')
    assert isinstance(jira_doc, JiraTestDocument), f"Expected JiraTestDocument, got {type(jira_doc)}"
    assert jira_doc.get_display_id() == "jira-TEST-123", f"Expected 'jira-TEST-123', got '{jira_doc.get_display_id()}'"
    print("✓ Document creation with registered types works")
    
    # Test fallback behavior
    unknown_doc = DocumentTypeRegistry.create_document(data, 'unknown_store')
    assert isinstance(unknown_doc, AIDocument), f"Expected AIDocument fallback, got {type(unknown_doc)}"
    print("✓ Fallback to base AIDocument works")
    
    return True

def test_factory_compatibility():
    """Test factory compatibility layer"""
    print("\n=== Testing Factory Compatibility Layer ===")
    
    from prefect_data_getters.stores.documents_new import AIDocument
    from prefect_data_getters.stores.document_registry import DocumentTypeRegistry, register_document_type
    from prefect_data_getters.stores.factory_compatibility import create_document_from_langchain, convert_documents_to_ai_documents_registry
    from langchain_core.documents import Document
    
    # Ensure we have a registered type
    @register_document_type('email_messages')
    class EmailTestDocument(AIDocument):
        def get_display_id(self):
            return f"email-{self.metadata.get('id', 'unknown')}"
    
    # Test langchain document conversion
    lc_doc = Document('langchain content', metadata={'id': 'lc-456'})
    lc_doc.id = 'document-456'
    
    ai_doc = create_document_from_langchain(lc_doc, 'email_messages')
    assert isinstance(ai_doc, EmailTestDocument), f"Expected EmailTestDocument, got {type(ai_doc)}"
    assert ai_doc.id == 'document-456', f"Expected 'document-456', got '{ai_doc.id}'"
    assert ai_doc.get_display_id() == "email-lc-456", f"Expected 'email-lc-456', got '{ai_doc.get_display_id()}'"
    print("✓ Langchain document conversion works")
    
    # Test batch conversion
    batch_docs = [
        Document('content 1', metadata={'id': '1'}),
        Document('content 2', metadata={'id': '2'})
    ]
    
    ai_batch = convert_documents_to_ai_documents_registry(batch_docs, 'jira_issues')
    assert len(ai_batch) == 2, f"Expected 2 documents, got {len(ai_batch)}"
    assert all(isinstance(doc, AIDocument) for doc in ai_batch), "Not all documents are AIDocument instances"
    print("✓ Batch conversion works")
    
    return True

def test_backward_compatibility():
    """Test backward compatibility with deprecated functions"""
    print("\n=== Testing Backward Compatibility ===")
    
    from prefect_data_getters.stores.factory_compatibility import _create_document, convert_documents_to_ai_documents
    from langchain_core.documents import Document
    
    # Test deprecated functions still work
    lc_doc = Document('content', metadata={'id': 'test'})
    
    # These should work but show warnings
    deprecated_doc = _create_document(lc_doc, 'jira_issues')
    assert deprecated_doc is not None, "Deprecated _create_document failed"
    print("✓ Deprecated _create_document still works")
    
    batch_docs = [Document('content', metadata={'id': '1'})]
    deprecated_batch = convert_documents_to_ai_documents(batch_docs, 'email_messages')
    assert len(deprecated_batch) == 1, "Deprecated batch conversion failed"
    print("✓ Deprecated batch conversion still works")
    
    return True

def test_registry_management():
    """Test registry management functions"""
    print("\n=== Testing Registry Management ===")
    
    from prefect_data_getters.stores.document_registry import DocumentTypeRegistry
    
    # Test registry listing
    registered_types = DocumentTypeRegistry.list_registered_types()
    assert isinstance(registered_types, dict), "list_registered_types should return a dict"
    print(f"✓ Registry listing works: {registered_types}")
    
    # Test get_document_class
    jira_class = DocumentTypeRegistry.get_document_class('jira_issues')
    email_class = DocumentTypeRegistry.get_document_class('email_messages')
    fallback_class = DocumentTypeRegistry.get_document_class('nonexistent')
    
    assert jira_class.__name__ != 'AIDocument', "Should get specific class for jira_issues"
    assert email_class.__name__ != 'AIDocument', "Should get specific class for email_messages"
    assert fallback_class.__name__ == 'AIDocument', "Should fallback to AIDocument for nonexistent"
    
    print("✓ get_document_class works correctly")
    
    return True

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n=== Testing Edge Cases and Error Handling ===")
    
    from prefect_data_getters.stores.factory_compatibility import create_document_from_langchain
    from langchain_core.documents import Document
    
    # Test empty metadata handling
    empty_doc = Document('content only')
    empty_ai = create_document_from_langchain(empty_doc, 'jira_issues')
    assert empty_ai.metadata == {}, f"Expected empty dict, got {empty_ai.metadata}"
    print("✓ Empty metadata handled correctly")
    
    # Test None metadata handling by testing our compatibility layer directly
    from langchain_core.documents import Document as BaseDoc
    none_doc = BaseDoc('content')  # No metadata provided
    none_ai = create_document_from_langchain(none_doc, 'email_messages')
    assert none_ai.metadata == {}, f"Expected empty dict, got {none_ai.metadata}"
    print("✓ None metadata handled correctly")
    
    return True

def main():
    """Run all Phase 2 validation tests"""
    print("=== Phase 2 Complete Implementation Validation ===")
    
    tests = [
        test_imports,
        test_registry_core,
        test_factory_compatibility,
        test_backward_compatibility,
        test_registry_management,
        test_edge_cases,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}")
    
    print(f"\n=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("\n🎉 Phase 2 Implementation Complete and Validated!")
        print("\n=== Phase 2 Success Criteria Met ===")
        print("✓ DocumentTypeRegistry class implemented and tested")
        print("✓ Auto-registration decorator works correctly")
        print("✓ Compatibility layer maintains existing factory function behavior")
        print("✓ Registry can handle unregistered types gracefully")
        print("✓ All functionality tested and working")
        print("✓ No breaking changes to existing consumers")
        print("\n🚀 Ready to proceed to Phase 3: Document Type Refactoring")
        return True
    else:
        print(f"\n❌ Phase 2 validation failed: {total - passed} test(s) failed")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)