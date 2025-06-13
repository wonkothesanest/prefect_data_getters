"""
Unit tests for BaseExporter abstract class.

Tests that the BaseExporter class properly enforces the abstract interface
and provides the expected utility methods for concrete implementations.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Iterator, Dict, Any
from langchain_core.documents import Document

from prefect_data_getters.exporters.base import BaseExporter


class ConcreteExporter(BaseExporter):
    """Concrete implementation for testing purposes."""
    
    def export(self, **kwargs) -> Iterator[Dict[str, Any]]:
        """Test implementation that yields raw test data."""
        test_data = [
            {"id": "1", "content": "Test message 1", "type": "test"},
            {"id": "2", "content": "Test message 2", "type": "test"}
        ]
        for data in test_data:
            yield data
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """Test implementation that processes raw data into documents."""
        for data in raw_data:
            doc = Document(
                page_content=data["content"],
                metadata={"source": "test", "message_id": data["id"]}
            )
            yield doc


class TestBaseExporter:
    """Test cases for BaseExporter abstract class."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseExporter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseExporter()
    
    def test_concrete_class_can_be_instantiated(self):
        """Test that concrete implementations can be instantiated."""
        exporter = ConcreteExporter()
        assert isinstance(exporter, BaseExporter)
        assert exporter.config == {}
    
    def test_concrete_class_with_config(self):
        """Test that concrete implementations accept configuration."""
        config = {"api_key": "test_key", "timeout": 30}
        exporter = ConcreteExporter(config=config)
        assert exporter.config == config
    
    def test_export_method_works(self):
        """Test that the export method works in concrete implementation."""
        exporter = ConcreteExporter()
        raw_data = list(exporter.export())
        
        assert len(raw_data) == 2
        assert all(isinstance(data, dict) for data in raw_data)
        assert raw_data[0]["content"] == "Test message 1"
        assert raw_data[1]["content"] == "Test message 2"
    
    def test_process_method_works(self):
        """Test that the process method works in concrete implementation."""
        exporter = ConcreteExporter()
        raw_data = [
            {"id": "1", "content": "Test message 1", "type": "test"},
            {"id": "2", "content": "Test message 2", "type": "test"}
        ]
        documents = list(exporter.process(iter(raw_data)))
        
        assert len(documents) == 2
        assert all(isinstance(doc, Document) for doc in documents)
        assert documents[0].page_content == "Test message 1"
        assert documents[1].page_content == "Test message 2"
    
    def test_export_documents_convenience_method(self):
        """Test that the export_documents convenience method works."""
        exporter = ConcreteExporter()
        documents = list(exporter.export_documents())
        
        assert len(documents) == 2
        assert all(isinstance(doc, Document) for doc in documents)
        assert documents[0].page_content == "Test message 1"
        assert documents[1].page_content == "Test message 2"
    
    def test_handle_authentication_error(self):
        """Test authentication error handling."""
        exporter = ConcreteExporter()
        test_error = Exception("Authentication failed")
        
        with pytest.raises(Exception, match="Authentication failed"):
            exporter._handle_authentication_error(test_error)
    
    def test_handle_api_error(self):
        """Test API error handling."""
        exporter = ConcreteExporter()
        test_error = Exception("API request failed")
        
        with pytest.raises(Exception, match="API request failed"):
            exporter._handle_api_error(test_error, "data fetch")
    
    def test_handle_api_error_without_context(self):
        """Test API error handling without context."""
        exporter = ConcreteExporter()
        test_error = Exception("API request failed")
        
        with pytest.raises(Exception, match="API request failed"):
            exporter._handle_api_error(test_error)
    
    def test_log_export_start(self):
        """Test export start logging."""
        exporter = ConcreteExporter()
        with patch.object(exporter.logger, 'info') as mock_info:
            exporter._log_export_start(days_ago=7, max_results=100)
            
            # Verify logger was called
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "Starting export" in call_args
            assert "days_ago=7" in call_args
            assert "max_results=100" in call_args
    
    def test_log_export_complete(self):
        """Test export completion logging."""
        exporter = ConcreteExporter()
        with patch.object(exporter.logger, 'info') as mock_info:
            exporter._log_export_complete(42)
            
            # Verify logger was called
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "Completed export" in call_args
            assert "42 documents" in call_args
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        config = {"api_key": "test", "endpoint": "https://api.test.com"}
        exporter = ConcreteExporter(config=config)
        
        # Should not raise any exception
        exporter._validate_config(["api_key", "endpoint"])
    
    def test_validate_config_missing_keys(self):
        """Test configuration validation with missing keys."""
        config = {"api_key": "test"}
        exporter = ConcreteExporter(config=config)
        
        with pytest.raises(ValueError, match="missing required configuration keys"):
            exporter._validate_config(["api_key", "endpoint", "timeout"])
    
    def test_validate_config_empty_config(self):
        """Test configuration validation with empty config."""
        exporter = ConcreteExporter()
        
        with pytest.raises(ValueError, match="missing required configuration keys"):
            exporter._validate_config(["api_key"])
    
    def test_logger_has_class_name(self):
        """Test that logger includes the class name."""
        exporter = ConcreteExporter()
        assert "ConcreteExporter" in exporter.logger.name


class IncompleteExporter(BaseExporter):
    """Incomplete implementation missing abstract methods."""
    pass

class PartialExporter(BaseExporter):
    """Partial implementation missing process method."""
    
    def export(self, **kwargs):
        return iter([{"test": "data"}])


class TestAbstractEnforcement:
    """Test that abstract methods are properly enforced."""
    
    def test_incomplete_implementation_fails(self):
        """Test that classes missing abstract methods cannot be instantiated."""
        with pytest.raises(TypeError):
            IncompleteExporter()
    
    def test_partial_implementation_fails(self):
        """Test that classes missing some abstract methods cannot be instantiated."""
        with pytest.raises(TypeError):
            PartialExporter()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_none_config_handled(self):
        """Test that None config is handled properly."""
        exporter = ConcreteExporter(config=None)
        assert exporter.config == {}
    
    def test_empty_export_iterator(self):
        """Test handling of empty export results."""
        class EmptyExporter(BaseExporter):
            def export(self, **kwargs) -> Iterator[Dict[str, Any]]:
                return iter([])
            
            def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
                return iter([])
        
        exporter = EmptyExporter()
        raw_data = list(exporter.export())
        assert len(raw_data) == 0
        
        documents = list(exporter.process(iter(raw_data)))
        assert len(documents) == 0
    
    def test_export_with_kwargs(self):
        """Test that export method receives kwargs properly."""
        class KwargsExporter(BaseExporter):
            def export(self, test_param=None, **kwargs) -> Iterator[Dict[str, Any]]:
                data = {
                    "param": test_param,
                    "kwargs": kwargs
                }
                yield data
            
            def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
                for data in raw_data:
                    doc = Document(
                        page_content=f"Param: {data['param']}",
                        metadata={"kwargs": str(data['kwargs'])}
                    )
                    yield doc
        
        exporter = KwargsExporter()
        raw_data = list(exporter.export(test_param="test_value", extra="extra_value"))
        documents = list(exporter.process(iter(raw_data)))
        
        assert len(documents) == 1
        assert "test_value" in documents[0].page_content
        assert "extra" in documents[0].metadata["kwargs"]