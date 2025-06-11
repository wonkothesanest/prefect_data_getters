import unittest
from ..stores.documents_new import AIDocument
from ..stores.compatibility import DocumentMigrationHelper
from langchain_core.documents import Document

class TestPhase1Refactoring(unittest.TestCase):
    """Test suite for Phase 1 refactoring changes"""
    
    def test_aidocument_inheritance(self):
        """Test that new AIDocument properly inherits from Document"""
        doc = AIDocument("test content", {"key": "value"})
        
        # Test inheritance
        self.assertIsInstance(doc, Document)
        
        # Test properties
        self.assertEqual(doc.page_content, "test content")
        self.assertEqual(doc.metadata["key"], "value")
        self.assertEqual(doc.document_type, "AIDocument")
    
    def test_document_type_property(self):
        """Test that document_type uses class name"""
        doc = AIDocument("content")
        self.assertEqual(doc.document_type, "AIDocument")
        
        # Test with subclass
        class TestDocument(AIDocument):
            pass
        
        test_doc = TestDocument("content")
        self.assertEqual(test_doc.document_type, "TestDocument")
    
    def test_get_display_id(self):
        """Test display ID functionality"""
        # Test without ID
        doc = AIDocument("content")
        self.assertEqual(doc.get_display_id(), "Unknown")
        
        # Test with ID
        doc.id = "test-123"
        self.assertEqual(doc.get_display_id(), "test-123")
    
    def test_metadata_helper(self):
        """Test metadata helper method"""
        metadata = {"key1": "value1", "key2": None}
        doc = AIDocument("content", metadata)
        
        self.assertEqual(doc._get_metadata("key1"), "value1")
        self.assertIsNone(doc._get_metadata("key2"))
        self.assertIsNone(doc._get_metadata("nonexistent"))
        self.assertEqual(doc._get_metadata("nonexistent", "default"), "default")
    
    def test_context_section(self):
        """Test context section formatting"""
        # Test without context
        doc = AIDocument("content", {})
        self.assertEqual(doc._context_section(), "")
        
        # Test with context
        doc_with_context = AIDocument("content", {"context": "test context"})
        context_section = doc_with_context._context_section()
        self.assertIn("Context:", context_section)
        self.assertIn("test context", context_section)
        self.assertIn(">>>>>>>>>>>>", context_section)
    
    def test_format_document_string(self):
        """Test document string formatting"""
        doc = AIDocument("test content", {"key": "value"})
        doc.id = "test-123"
        
        formatted = doc._format_document_string({"Test Field": "test value"})
        
        self.assertIn("Document Type: AIDocument", formatted)
        self.assertIn("Test Field: test value", formatted)
        self.assertIn("test content", formatted)
        self.assertIn("END: test-123", formatted)
    
    def test_default_str_representation(self):
        """Test default string representation"""
        doc = AIDocument("test content", {"key": "value"})
        doc.id = "test-123"
        
        str_repr = str(doc)
        self.assertIn("Document Type: AIDocument", str_repr)
        self.assertIn("test content", str_repr)
        self.assertIn("END: test-123", str_repr)
    
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
        self.assertEqual(doc_dict, expected_dict)
        
        # Convert back from dict
        restored_doc = AIDocument.from_dict(doc_dict)
        self.assertEqual(restored_doc.page_content, original_doc.page_content)
        self.assertEqual(restored_doc.metadata, original_doc.metadata)
        self.assertEqual(restored_doc.id, original_doc.id)
    
    def test_from_dict_without_id(self):
        """Test from_dict when no ID is provided"""
        data = {
            'page_content': 'test content',
            'metadata': {'key': 'value'},
            'document_type': 'AIDocument'
        }
        
        doc = AIDocument.from_dict(data)
        self.assertEqual(doc.page_content, 'test content')
        self.assertEqual(doc.metadata, {'key': 'value'})
        self.assertTrue(not hasattr(doc, 'id') or doc.id is None)
    
    def test_search_score_property(self):
        """Test search_score property initialization and assignment"""
        doc = AIDocument("content")
        self.assertIsNone(doc.search_score)
        
        doc.search_score = 0.85
        self.assertEqual(doc.search_score, 0.85)
    
    def test_compatibility_conversion(self):
        """Test backward compatibility conversion"""
        # Create base Document
        base_doc = Document(page_content="test content", metadata={"key": "value"})
        base_doc.id = "test-123"
        
        # Convert to new AIDocument
        ai_doc = DocumentMigrationHelper.convert_document_to_new(base_doc)
        
        self.assertIsInstance(ai_doc, AIDocument)
        self.assertEqual(ai_doc.page_content, "test content")
        self.assertEqual(ai_doc.metadata["key"], "value")
        self.assertEqual(ai_doc.id, "test-123")
    
    def test_batch_convert_documents(self):
        """Test batch conversion of documents"""
        # Create multiple base Documents
        docs = [
            Document(page_content="content 1", metadata={"key": "value1"}),
            Document(page_content="content 2", metadata={"key": "value2"}),
            Document(page_content="content 3", metadata={"key": "value3"})
        ]
        
        # Set IDs
        for i, doc in enumerate(docs):
            doc.id = f"test-{i+1}"
        
        # Convert batch
        ai_docs = DocumentMigrationHelper.batch_convert_documents(docs)
        
        self.assertEqual(len(ai_docs), 3)
        for i, ai_doc in enumerate(ai_docs):
            self.assertIsInstance(ai_doc, AIDocument)
            self.assertEqual(ai_doc.page_content, f"content {i+1}")
            self.assertEqual(ai_doc.metadata["key"], f"value{i+1}")
            self.assertEqual(ai_doc.id, f"test-{i+1}")
    
    def test_empty_metadata_handling(self):
        """Test handling of empty or None metadata"""
        # Test with None metadata
        doc1 = AIDocument("content", None)
        self.assertEqual(doc1.metadata, {})
        self.assertIsNone(doc1._get_metadata("any_key"))
        
        # Test with empty metadata
        doc2 = AIDocument("content", {})
        self.assertEqual(doc2.metadata, {})
        self.assertIsNone(doc2._get_metadata("any_key"))
    
    def test_inheritance_compatibility(self):
        """Test that new AIDocument can be used as a Document"""
        doc = AIDocument("test content", {"key": "value"})
        
        # Should work with functions expecting Document
        def process_document(document: Document) -> str:
            return f"Processing: {document.page_content}"
        
        result = process_document(doc)
        self.assertEqual(result, "Processing: test content")
    
    def test_subclass_document_type(self):
        """Test document_type property with subclasses"""
        class CustomDocument(AIDocument):
            def __init__(self, content, metadata=None):
                super().__init__(content, metadata)
        
        custom_doc = CustomDocument("custom content")
        self.assertEqual(custom_doc.document_type, "CustomDocument")
        self.assertIsInstance(custom_doc, AIDocument)
        self.assertIsInstance(custom_doc, Document)
    
    def test_subclass_get_display_id_override(self):
        """Test that subclasses can override get_display_id"""
        class CustomDocument(AIDocument):
            def get_display_id(self) -> str:
                return f"CUSTOM-{self._get_metadata('custom_id', 'unknown')}"
        
        custom_doc = CustomDocument("content", {"custom_id": "123"})
        self.assertEqual(custom_doc.get_display_id(), "CUSTOM-123")
        
        custom_doc_no_id = CustomDocument("content", {})
        self.assertEqual(custom_doc_no_id.get_display_id(), "CUSTOM-unknown")


if __name__ == '__main__':
    unittest.main()