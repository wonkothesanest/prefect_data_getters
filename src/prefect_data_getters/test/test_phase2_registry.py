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
        langchain_doc = Document("test content", metadata={"key": "value"})
        langchain_doc.id = "test-123"
        
        ai_doc = create_document_from_langchain(langchain_doc, "test_store")
        
        assert isinstance(ai_doc, TestDocument)
        assert ai_doc.page_content == "test content"
        assert ai_doc.metadata["key"] == "value"
        assert ai_doc.id == "test-123"
        
        # Test batch conversion
        langchain_docs = [
            Document("content1", metadata={"id": "1"}),
            Document("content2", metadata={"id": "2"})
        ]
        
        ai_docs = convert_documents_to_ai_documents_registry(langchain_docs, "test_store")
        
        assert len(ai_docs) == 2
        assert all(isinstance(doc, TestDocument) for doc in ai_docs)
        assert ai_docs[0].page_content == "content1"
        assert ai_docs[1].page_content == "content2"
    
    def test_registry_state_persistence(self):
        """Test that registry state persists across calls"""
        @register_document_type("persistent_store")
        class PersistentDocument(AIDocument):
            pass
        
        # Check registration persists
        assert DocumentTypeRegistry.is_registered("persistent_store")
        
        # Create document to ensure it still works
        data = {'page_content': 'test', 'metadata': {}}
        doc = DocumentTypeRegistry.create_document(data, "persistent_store")
        assert isinstance(doc, PersistentDocument)
        
        # Check it's still registered after creation
        assert DocumentTypeRegistry.is_registered("persistent_store")
    
    def test_multiple_registrations_same_store(self):
        """Test that registering multiple classes for same store overwrites"""
        class FirstDocument(AIDocument):
            pass
        
        class SecondDocument(AIDocument):
            pass
        
        DocumentTypeRegistry.register("same_store", FirstDocument)
        assert DocumentTypeRegistry.get_document_class("same_store") == FirstDocument
        
        DocumentTypeRegistry.register("same_store", SecondDocument)
        assert DocumentTypeRegistry.get_document_class("same_store") == SecondDocument
    
    def test_get_document_class_unregistered(self):
        """Test getting document class for unregistered store returns base class"""
        doc_class = DocumentTypeRegistry.get_document_class("nonexistent_store")
        assert doc_class == AIDocument
    
    def test_clear_registry(self):
        """Test clearing registry removes all registrations"""
        @register_document_type("temp_store")
        class TempDocument(AIDocument):
            pass
        
        assert DocumentTypeRegistry.is_registered("temp_store")
        
        DocumentTypeRegistry.clear_registry()
        
        assert not DocumentTypeRegistry.is_registered("temp_store")
        assert DocumentTypeRegistry.get_document_class("temp_store") == AIDocument

class TestFactoryCompatibility:
    """Test suite for factory compatibility layer"""
    
    def setup_method(self):
        """Clear registry before each test"""
        DocumentTypeRegistry.clear_registry()
    
    def test_create_document_from_langchain_basic(self):
        """Test basic document creation from langchain document"""
        langchain_doc = Document("test content", metadata={"test": "metadata"})
        ai_doc = create_document_from_langchain(langchain_doc, "jira_issues")
        
        assert isinstance(ai_doc, AIDocument)
        assert ai_doc.page_content == "test content"
        assert ai_doc.metadata["test"] == "metadata"
    
    def test_create_document_from_langchain_with_id(self):
        """Test document creation preserves ID"""
        langchain_doc = Document("content", metadata={"meta": "data"})
        langchain_doc.id = "doc-123"
        
        ai_doc = create_document_from_langchain(langchain_doc, "email_messages")
        
        assert ai_doc.id == "doc-123"
        assert ai_doc.page_content == "content"
        assert ai_doc.metadata["meta"] == "data"
    
    def test_convert_documents_batch(self):
        """Test batch conversion of documents"""
        docs = [
            Document("content1", metadata={"id": "1"}),
            Document("content2", metadata={"id": "2"}),
            Document("content3", metadata={"id": "3"})
        ]
        
        ai_docs = convert_documents_to_ai_documents_registry(docs, "slack_messages")
        
        assert len(ai_docs) == 3
        assert all(isinstance(doc, AIDocument) for doc in ai_docs)
        assert [doc.page_content for doc in ai_docs] == ["content1", "content2", "content3"]
        assert [doc.metadata["id"] for doc in ai_docs] == ["1", "2", "3"]
    
    def test_empty_metadata_handling(self):
        """Test handling of documents with no metadata"""
        langchain_doc = Document("content only")
        ai_doc = create_document_from_langchain(langchain_doc, "slab_documents")
        
        assert isinstance(ai_doc, AIDocument)
        assert ai_doc.page_content == "content only"
        assert ai_doc.metadata == {}
    
    def test_none_metadata_handling(self):
        """Test handling of documents with None metadata"""
        langchain_doc = Document("content", metadata=None)
        ai_doc = create_document_from_langchain(langchain_doc, "bitbucket_pull_requests")
        
        assert isinstance(ai_doc, AIDocument)
        assert ai_doc.page_content == "content"
        assert ai_doc.metadata == {}