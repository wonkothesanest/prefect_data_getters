"""
Unit tests for processing functions in exporters module.

Tests all the composable processing functions that work with document iterators,
including edge cases, error handling, and integration scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Iterator
from langchain_core.documents import Document

from prefect_data_getters.exporters import (
    add_ingestion_timestamp,
    convert_to_ai_documents,
    filter_by_metadata,
    add_source_metadata,
    batch_documents,
    add_default_metadata
)
from prefect_data_getters.stores.documents_new import AIDocument


class TestAddIngestionTimestamp:
    """Test cases for add_ingestion_timestamp function."""
    
    def test_adds_timestamp_to_documents(self):
        """Test that timestamp is added to document metadata."""
        docs = [
            Document(page_content="Test 1", metadata={"source": "test"}),
            Document(page_content="Test 2", metadata={"author": "user"})
        ]
        
        processed = list(add_ingestion_timestamp(iter(docs)))
        
        assert len(processed) == 2
        for doc in processed:
            assert "ingestion_timestamp" in doc.metadata
            # Verify timestamp format (ISO format)
            timestamp = doc.metadata["ingestion_timestamp"]
            datetime.fromisoformat(timestamp)  # Should not raise exception
    
    def test_custom_metadata_field(self):
        """Test using custom metadata field name."""
        docs = [Document(page_content="Test", metadata={})]
        
        processed = list(add_ingestion_timestamp(iter(docs), metadata_field="processed_at"))
        
        assert "processed_at" in processed[0].metadata
        assert "ingestion_timestamp" not in processed[0].metadata
    
    def test_handles_none_metadata(self):
        """Test handling documents with empty metadata."""
        docs = [Document(page_content="Test", metadata={})]
        
        processed = list(add_ingestion_timestamp(iter(docs)))
        
        assert processed[0].metadata is not None
        assert "ingestion_timestamp" in processed[0].metadata
    
    def test_preserves_existing_metadata(self):
        """Test that existing metadata is preserved."""
        docs = [Document(page_content="Test", metadata={"existing": "value"})]
        
        processed = list(add_ingestion_timestamp(iter(docs)))
        
        assert processed[0].metadata["existing"] == "value"
        assert "ingestion_timestamp" in processed[0].metadata
    
    def test_empty_iterator(self):
        """Test handling empty document iterator."""
        processed = list(add_ingestion_timestamp(iter([])))
        assert len(processed) == 0
    
    def test_error_handling(self):
        """Test error handling with malformed documents."""
        # Create a mock document that raises an exception when accessing metadata
        mock_doc = Mock(spec=Document)
        mock_doc.page_content = "Test"
        mock_doc.metadata = None
        
        # Make metadata assignment raise an exception
        def side_effect(value):
            raise Exception("Metadata error")
        
        type(mock_doc).metadata = property(lambda self: None, side_effect)
        
        docs = [mock_doc]
        
        # Should not raise exception, but yield the document anyway
        processed = list(add_ingestion_timestamp(iter(docs)))
        assert len(processed) == 1


class TestConvertToAIDocuments:
    """Test cases for convert_to_ai_documents function."""
    
    @patch('prefect_data_getters.exporters.DocumentTypeRegistry')
    def test_converts_documents_to_ai_documents(self, mock_registry):
        """Test successful conversion to AIDocuments."""
        # Setup mock
        mock_ai_doc = Mock(spec=AIDocument)
        mock_registry.create_document.return_value = mock_ai_doc
        
        docs = [
            Document(page_content="Test 1", metadata={"source": "test"}),
            Document(page_content="Test 2", metadata={"author": "user"})
        ]
        
        processed = list(convert_to_ai_documents(iter(docs), "email_messages"))
        
        assert len(processed) == 2
        assert mock_registry.create_document.call_count == 2
        
        # Verify correct data passed to registry
        call_args = mock_registry.create_document.call_args_list
        assert call_args[0][0][0]['page_content'] == "Test 1"
        assert call_args[0][0][1] == "email_messages"
    
    @patch('prefect_data_getters.exporters.DocumentTypeRegistry')
    def test_preserves_document_id(self, mock_registry):
        """Test that document IDs are preserved."""
        mock_ai_doc = Mock(spec=AIDocument)
        mock_registry.create_document.return_value = mock_ai_doc
        
        doc = Document(page_content="Test", metadata={})
        doc.id = "test_id_123"
        
        processed = list(convert_to_ai_documents(iter([doc]), "email_messages"))
        
        # Verify ID was set on the AI document
        assert mock_ai_doc.id == "test_id_123"
    
    @patch('prefect_data_getters.exporters.DocumentTypeRegistry')
    def test_handles_empty_metadata(self, mock_registry):
        """Test handling documents with empty metadata."""
        mock_ai_doc = Mock(spec=AIDocument)
        mock_registry.create_document.return_value = mock_ai_doc
        
        doc = Document(page_content="Test", metadata={})
        
        processed = list(convert_to_ai_documents(iter([doc]), "email_messages"))
        
        # Verify empty dict was passed for metadata
        call_args = mock_registry.create_document.call_args[0][0]
        assert call_args['metadata'] == {}
    
    @patch('prefect_data_getters.exporters.DocumentTypeRegistry')
    def test_error_handling(self, mock_registry):
        """Test error handling when conversion fails."""
        mock_registry.create_document.side_effect = Exception("Registry error")
        
        docs = [Document(page_content="Test", metadata={})]
        
        # Should not raise exception, but skip the problematic document
        processed = list(convert_to_ai_documents(iter(docs), "email_messages"))
        assert len(processed) == 0
    
    def test_empty_iterator(self):
        """Test handling empty document iterator."""
        processed = list(convert_to_ai_documents(iter([]), "email_messages"))
        assert len(processed) == 0


class TestFilterByMetadata:
    """Test cases for filter_by_metadata function."""
    
    def test_exact_match_filtering(self):
        """Test exact match filtering."""
        docs = [
            Document(page_content="Test 1", metadata={"status": "active"}),
            Document(page_content="Test 2", metadata={"status": "inactive"}),
            Document(page_content="Test 3", metadata={"status": "active"})
        ]
        
        filtered = list(filter_by_metadata(iter(docs), "status", "active", exact_match=True))
        
        assert len(filtered) == 2
        assert all(doc.metadata["status"] == "active" for doc in filtered)
    
    def test_partial_match_filtering(self):
        """Test partial match filtering."""
        docs = [
            Document(page_content="Test 1", metadata={"subject": "Important Meeting"}),
            Document(page_content="Test 2", metadata={"subject": "Daily Standup"}),
            Document(page_content="Test 3", metadata={"subject": "Meeting Notes"})
        ]
        
        filtered = list(filter_by_metadata(iter(docs), "subject", "meeting", exact_match=False))
        
        assert len(filtered) == 2
        assert "Meeting" in filtered[0].metadata["subject"]
        assert "Meeting" in filtered[1].metadata["subject"]
    
    def test_missing_metadata_key(self):
        """Test filtering when metadata key is missing."""
        docs = [
            Document(page_content="Test 1", metadata={"status": "active"}),
            Document(page_content="Test 2", metadata={"other": "value"}),
        ]
        
        filtered = list(filter_by_metadata(iter(docs), "status", "active"))
        
        assert len(filtered) == 1
        assert filtered[0].metadata["status"] == "active"
    
    def test_empty_metadata(self):
        """Test filtering documents with empty metadata."""
        docs = [
            Document(page_content="Test 1", metadata={}),
            Document(page_content="Test 2", metadata={"status": "active"}),
        ]
        
        filtered = list(filter_by_metadata(iter(docs), "status", "active"))
        
        assert len(filtered) == 1
        assert filtered[0].metadata["status"] == "active"
    
    def test_empty_iterator(self):
        """Test filtering empty iterator."""
        filtered = list(filter_by_metadata(iter([]), "status", "active"))
        assert len(filtered) == 0


class TestAddSourceMetadata:
    """Test cases for add_source_metadata function."""
    
    def test_adds_source_name(self):
        """Test adding source name to metadata."""
        docs = [Document(page_content="Test", metadata={"existing": "value"})]
        
        processed = list(add_source_metadata(iter(docs), "gmail"))
        
        assert processed[0].metadata["source_name"] == "gmail"
        assert processed[0].metadata["existing"] == "value"
    
    def test_adds_source_name_and_type(self):
        """Test adding both source name and type."""
        docs = [Document(page_content="Test", metadata={})]
        
        processed = list(add_source_metadata(iter(docs), "gmail", "email"))
        
        assert processed[0].metadata["source_name"] == "gmail"
        assert processed[0].metadata["source_type"] == "email"
    
    def test_handles_empty_metadata(self):
        """Test handling documents with empty metadata."""
        docs = [Document(page_content="Test", metadata={})]
        
        processed = list(add_source_metadata(iter(docs), "slack", "chat"))
        
        assert processed[0].metadata["source_name"] == "slack"
        assert processed[0].metadata["source_type"] == "chat"
    
    def test_empty_iterator(self):
        """Test handling empty iterator."""
        processed = list(add_source_metadata(iter([]), "gmail"))
        assert len(processed) == 0


class TestBatchDocuments:
    """Test cases for batch_documents function."""
    
    def test_creates_batches(self):
        """Test creating batches of specified size."""
        docs = [Document(page_content=f"Test {i}") for i in range(5)]
        
        batches = list(batch_documents(iter(docs), batch_size=2))
        
        assert len(batches) == 3  # 2 + 2 + 1
        assert len(batches[0]) == 2
        assert len(batches[1]) == 2
        assert len(batches[2]) == 1
    
    def test_exact_batch_size(self):
        """Test when documents exactly fill batches."""
        docs = [Document(page_content=f"Test {i}") for i in range(4)]
        
        batches = list(batch_documents(iter(docs), batch_size=2))
        
        assert len(batches) == 2
        assert all(len(batch) == 2 for batch in batches)
    
    def test_single_document(self):
        """Test batching single document."""
        docs = [Document(page_content="Test")]
        
        batches = list(batch_documents(iter(docs), batch_size=5))
        
        assert len(batches) == 1
        assert len(batches[0]) == 1
    
    def test_empty_iterator(self):
        """Test batching empty iterator."""
        batches = list(batch_documents(iter([]), batch_size=2))
        assert len(batches) == 0
    
    def test_large_batch_size(self):
        """Test batch size larger than document count."""
        docs = [Document(page_content=f"Test {i}") for i in range(3)]
        
        batches = list(batch_documents(iter(docs), batch_size=10))
        
        assert len(batches) == 1
        assert len(batches[0]) == 3


class TestLegacyFunction:
    """Test cases for legacy add_default_metadata function."""
    
    def test_legacy_function_works(self):
        """Test that legacy function still works."""
        docs = [Document(page_content="Test", metadata={})]
        
        with pytest.warns(DeprecationWarning):
            processed = add_default_metadata(docs)
        
        assert len(processed) == 1
        assert "ingestion_timestamp" in processed[0].metadata
    
    def test_legacy_function_returns_list(self):
        """Test that legacy function returns list, not iterator."""
        docs = [Document(page_content="Test", metadata={})]
        
        with pytest.warns(DeprecationWarning):
            processed = add_default_metadata(docs)
        
        assert isinstance(processed, list)


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple functions."""
    
    @patch('prefect_data_getters.exporters.DocumentTypeRegistry')
    def test_full_processing_pipeline(self, mock_registry):
        """Test complete processing pipeline."""
        mock_ai_doc = Mock(spec=AIDocument)
        mock_registry.create_document.return_value = mock_ai_doc
        
        # Start with raw documents
        docs = [
            Document(page_content="Email 1", metadata={"subject": "Important"}),
            Document(page_content="Email 2", metadata={"subject": "Daily Update"})
        ]
        
        # Apply processing pipeline
        timestamped = add_ingestion_timestamp(iter(docs))
        with_source = add_source_metadata(timestamped, "gmail", "email")
        filtered = filter_by_metadata(with_source, "subject", "Important")
        ai_docs = convert_to_ai_documents(filtered, "email_messages")
        
        result = list(ai_docs)
        
        # Should have one document (filtered)
        assert len(result) == 1
        assert mock_registry.create_document.called
    
    def test_error_recovery_in_pipeline(self):
        """Test that pipeline continues processing despite individual errors."""
        docs = [
            Document(page_content="Good doc", metadata={"status": "ok"}),
            Mock(spec=Document),  # This will cause errors
            Document(page_content="Another good doc", metadata={"status": "ok"})
        ]
        
        # Configure mock to raise exceptions
        docs[1].page_content = "Mock doc"
        docs[1].metadata = None
        
        # Process through pipeline - should handle errors gracefully
        timestamped = add_ingestion_timestamp(iter(docs))
        with_source = add_source_metadata(timestamped, "test")
        
        result = list(with_source)
        
        # Should get at least the good documents
        assert len(result) >= 2