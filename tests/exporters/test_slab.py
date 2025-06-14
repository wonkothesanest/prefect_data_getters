"""
Tests for SlabExporter class.

This module contains comprehensive tests for the SlabExporter implementation,
including unit tests for export and process methods, error handling, and integration tests.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from typing import Iterator

from langchain_core.documents import Document

from prefect_data_getters.exporters.slab_exporter import SlabExporter
from prefect_data_getters.exporters.base import BaseExporter


class TestSlabExporter:
    """Test cases for SlabExporter class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Disable chunking for most tests to get predictable document IDs
        self.exporter = SlabExporter({"split_documents": False})
        
        # Sample test data
        self.sample_users_data = {
            "data": {
                "session": {
                    "organization": {
                        "users": [
                            {"id": "user1", "name": "John Doe", "email": "john@example.com"},
                            {"id": "user2", "name": "Jane Smith", "email": "jane@example.com"}
                        ]
                    }
                }
            }
        }
        
        self.sample_topics_data = {
            "data": {
                "session": {
                    "organization": {
                        "topics": [
                            {"id": "topic1", "name": "Engineering", "parent": None},
                            {"id": "topic2", "name": "Backend", "parent": {"id": "topic1"}},
                            {"id": "topic3", "name": "API", "parent": {"id": "topic2"}}
                        ]
                    }
                }
            }
        }
        
        self.sample_metadata = {
            "data": {
                "post": {
                    "id": "doc123",
                    "title": "Test Document",
                    "owner": {"id": "user1"},
                    "contributors": [{"id": "user1"}, {"id": "user2"}],
                    "topics": [{"id": "topic3"}],
                    "updatedAt": "2023-01-15T10:30:00Z",
                    "insertedAt": "2023-01-10T09:00:00Z",
                    "__typename": "Post"
                }
            }
        }
        
        self.sample_content = "# Test Document\n\nThis is a test document content."
    
    def test_inheritance(self):
        """Test that SlabExporter properly inherits from BaseExporter."""
        assert isinstance(self.exporter, BaseExporter)
        assert hasattr(self.exporter, 'export')
        assert hasattr(self.exporter, 'process')
        assert hasattr(self.exporter, 'export_documents')
    
    def test_initialization_default_config(self):
        """Test SlabExporter initialization with default configuration."""
        exporter = SlabExporter()
        assert exporter._users_cache is None
        assert exporter._topics_cache is None
        # Semantic chunker may or may not be initialized depending on dependencies
    
    def test_initialization_custom_config(self):
        """Test SlabExporter initialization with custom configuration."""
        config = {
            "split_documents": False,
            "chunk_threshold": 100,
            "max_chunks": 5
        }
        exporter = SlabExporter(config)
        assert exporter._get_config("split_documents") is False
        assert exporter._get_config("chunk_threshold") == 100
        assert exporter._get_config("max_chunks") == 5
    
    @patch('glob.glob')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_export_success(self, mock_file, mock_exists, mock_glob):
        """Test successful export of Slab documents."""
        # Setup mocks
        mock_exists.return_value = True
        mock_glob.return_value = ['/backup/doc1.md', '/backup/doc2.md']
        
        # Mock file contents
        file_contents = {
            '/backup/doc1.md': self.sample_content,
            '/backup/doc1.json': json.dumps(self.sample_metadata),
            '/backup/doc2.md': "# Another Doc\n\nContent here.",
            '/backup/doc2.json': json.dumps(self.sample_metadata),
            '/backup/../allUsers.json': json.dumps(self.sample_users_data),
            '/backup/../allTopics.json': json.dumps(self.sample_topics_data)
        }
        
        def mock_open_func(filename, *args, **kwargs):
            return mock_open(read_data=file_contents.get(filename, "")).return_value
        
        mock_file.side_effect = mock_open_func
        
        # Test export
        results = list(self.exporter.export('/backup'))
        
        assert len(results) == 2
        assert all('doc_file' in result for result in results)
        assert all('meta_file' in result for result in results)
        assert all('content' in result for result in results)
        assert all('metadata' in result for result in results)
    
    def test_export_directory_not_found(self):
        """Test export with non-existent directory."""
        with pytest.raises(FileNotFoundError):
            list(self.exporter.export('/nonexistent'))
    
    @patch('glob.glob')
    @patch('os.path.exists')
    def test_export_no_files_found(self, mock_exists, mock_glob):
        """Test export when no files are found."""
        mock_exists.return_value = True
        mock_glob.return_value = []
        
        results = list(self.exporter.export('/backup'))
        assert len(results) == 0
    
    @patch('glob.glob')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_export_missing_metadata_file(self, mock_file, mock_exists, mock_glob):
        """Test export when metadata file is missing."""
        mock_exists.side_effect = lambda path: path == '/backup' or 'allUsers' in path or 'allTopics' in path
        mock_glob.return_value = ['/backup/doc1.md']
        
        file_contents = {
            '/backup/../allUsers.json': json.dumps(self.sample_users_data),
            '/backup/../allTopics.json': json.dumps(self.sample_topics_data)
        }
        
        def mock_open_func(filename, *args, **kwargs):
            return mock_open(read_data=file_contents.get(filename, "")).return_value
        
        mock_file.side_effect = mock_open_func
        
        results = list(self.exporter.export('/backup'))
        assert len(results) == 0  # Should skip files without metadata
    
    def test_process_success(self):
        """Test successful processing of raw Slab data."""
        # Setup exporter with cached data
        self.exporter._users_cache = {
            user['id']: user for user in self.sample_users_data['data']['session']['organization']['users']
        }
        self.exporter._topics_cache = {
            topic['id']: topic for topic in self.sample_topics_data['data']['session']['organization']['topics']
        }
        
        raw_data = [{
            "doc_file": "/backup/doc1.md",
            "meta_file": "/backup/doc1.json",
            "content": self.sample_content,
            "metadata": self.sample_metadata
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        
        assert len(results) == 1
        doc = results[0]
        assert isinstance(doc, Document)
        assert doc.id == "doc123"
        assert doc.page_content == self.sample_content
        assert doc.metadata['title'] == "Test Document"
        assert doc.metadata['owner'] == "John Doe - john@example.com"
        assert "Jane Smith - jane@example.com" in doc.metadata['contributors']
        assert "Engineering / Backend / API" in doc.metadata['topics']
    
    def test_process_invalid_metadata_structure(self):
        """Test processing with invalid metadata structure."""
        self.exporter._users_cache = {}
        self.exporter._topics_cache = {}
        
        raw_data = [{
            "doc_file": "/backup/doc1.md",
            "meta_file": "/backup/doc1.json",
            "content": self.sample_content,
            "metadata": {"invalid": "structure"}
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        assert len(results) == 0  # Should skip invalid metadata
    
    def test_process_with_chunking(self):
        """Test processing with semantic chunking enabled."""
        # Mock semantic chunker
        mock_chunker = Mock()
        mock_chunker.split_text.return_value = ["Chunk 1", "Chunk 2"]
        self.exporter._semantic_chunker = mock_chunker
        
        # Setup cached data
        self.exporter._users_cache = {
            user['id']: user for user in self.sample_users_data['data']['session']['organization']['users']
        }
        self.exporter._topics_cache = {
            topic['id']: topic for topic in self.sample_topics_data['data']['session']['organization']['topics']
        }
        
        raw_data = [{
            "doc_file": "/backup/doc1.md",
            "meta_file": "/backup/doc1.json",
            "content": self.sample_content,
            "metadata": self.sample_metadata
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        
        assert len(results) == 2  # Two chunks
        for i, doc in enumerate(results):
            assert doc.id == f"doc123_{i}"
            assert doc.metadata['type'] == "slab_chunk"
            assert doc.metadata['chunk_index'] == i
            assert doc.metadata['parent_document_id'] == "doc123"
    
    def test_export_documents_convenience_method(self):
        """Test the convenience method that combines export and process."""
        with patch.object(self.exporter, 'export') as mock_export, \
             patch.object(self.exporter, 'process') as mock_process:
            
            mock_export.return_value = iter([{"test": "data"}])
            mock_process.return_value = iter([Document(page_content="test")])
            
            results = list(self.exporter.export_documents(backup_dir='/backup'))
            
            assert len(results) == 1
            mock_export.assert_called_once_with(backup_dir='/backup')
            mock_process.assert_called_once()
    
    def test_get_user_info(self):
        """Test user information retrieval."""
        self.exporter._users_cache = {
            user['id']: user for user in self.sample_users_data['data']['session']['organization']['users']
        }
        
        # Test existing user
        user_info = self.exporter._get_user_info("user1")
        assert user_info == "John Doe - john@example.com"
        
        # Test non-existent user
        user_info = self.exporter._get_user_info("nonexistent")
        assert user_info == ""
        
        # Test with no cache
        self.exporter._users_cache = None
        user_info = self.exporter._get_user_info("user1")
        assert user_info == ""
    
    def test_get_contributors_info(self):
        """Test contributors information formatting."""
        self.exporter._users_cache = {
            user['id']: user for user in self.sample_users_data['data']['session']['organization']['users']
        }
        
        contributors = [{"id": "user1"}, {"id": "user2"}]
        result = self.exporter._get_contributors_info(contributors)
        
        assert "John Doe - john@example.com" in result
        assert "Jane Smith - jane@example.com" in result
        assert ", " in result
    
    def test_process_topics(self):
        """Test topic processing with hierarchy."""
        self.exporter._topics_cache = {
            topic['id']: topic for topic in self.sample_topics_data['data']['session']['organization']['topics']
        }
        
        topics = [{"id": "topic3"}]  # API topic
        result = self.exporter._process_topics(topics)
        
        assert len(result) == 1
        assert "Engineering / Backend / API" in result[0]
    
    def test_get_topic_ancestors(self):
        """Test topic ancestor retrieval."""
        self.exporter._topics_cache = {
            topic['id']: topic for topic in self.sample_topics_data['data']['session']['organization']['topics']
        }
        
        ancestors = self.exporter._get_topic_ancestors("topic3")
        
        assert len(ancestors) == 2
        assert ancestors[0]['name'] == "Backend"
        assert ancestors[1]['name'] == "Engineering"
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_load_users_and_topics_success(self, mock_exists, mock_file):
        """Test successful loading of users and topics data."""
        mock_exists.return_value = True
        
        file_contents = {
            '/allUsers.json': json.dumps(self.sample_users_data),
            '/allTopics.json': json.dumps(self.sample_topics_data)
        }
        
        def mock_open_func(filename, *args, **kwargs):
            return mock_open(read_data=file_contents.get(filename, "")).return_value
        
        mock_file.side_effect = mock_open_func
        
        self.exporter._load_users_and_topics('/backup')
        
        assert len(self.exporter._users_cache) == 2
        assert len(self.exporter._topics_cache) == 3
        assert "user1" in self.exporter._users_cache
        assert "topic1" in self.exporter._topics_cache
    
    @patch('os.path.exists')
    def test_load_users_and_topics_missing_files(self, mock_exists):
        """Test loading when users/topics files are missing."""
        mock_exists.return_value = False
        
        self.exporter._load_users_and_topics('/backup')
        
        assert self.exporter._users_cache == {}
        assert self.exporter._topics_cache == {}
    
    def test_error_handling_in_process(self):
        """Test error handling during document processing."""
        # Setup with invalid data that will cause errors
        raw_data = [
            {"invalid": "data"},  # Missing required fields
            {
                "doc_file": "/backup/doc1.md",
                "meta_file": "/backup/doc1.json",
                "content": self.sample_content,
                "metadata": self.sample_metadata
            }
        ]
        
        # Setup valid cached data for the second item
        self.exporter._users_cache = {
            user['id']: user for user in self.sample_users_data['data']['session']['organization']['users']
        }
        self.exporter._topics_cache = {
            topic['id']: topic for topic in self.sample_topics_data['data']['session']['organization']['topics']
        }
        
        results = list(self.exporter.process(iter(raw_data)))
        
        # Should process only the valid item
        assert len(results) == 1
        assert results[0].id == "doc123"
    
    def test_empty_content_handling(self):
        """Test handling of empty document content."""
        self.exporter._users_cache = {
            user['id']: user for user in self.sample_users_data['data']['session']['organization']['users']
        }
        self.exporter._topics_cache = {
            topic['id']: topic for topic in self.sample_topics_data['data']['session']['organization']['topics']
        }
        
        raw_data = [{
            "doc_file": "/backup/doc1.md",
            "meta_file": "/backup/doc1.json",
            "content": "",  # Empty content
            "metadata": self.sample_metadata
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        
        assert len(results) == 1
        assert results[0].page_content == ""
    
    def test_metadata_fields_completeness(self):
        """Test that all expected metadata fields are present."""
        self.exporter._users_cache = {
            user['id']: user for user in self.sample_users_data['data']['session']['organization']['users']
        }
        self.exporter._topics_cache = {
            topic['id']: topic for topic in self.sample_topics_data['data']['session']['organization']['topics']
        }
        
        raw_data = [{
            "doc_file": "/backup/doc1.md",
            "meta_file": "/backup/doc1.json",
            "content": self.sample_content,
            "metadata": self.sample_metadata
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        doc = results[0]
        
        expected_fields = [
            'document_id', 'title', 'owner', 'contributors', 'topics',
            'updated_at', 'created_at', 'slab_type', 'source', 'type',
            'ingestion_timestamp'
        ]
        
        for field in expected_fields:
            assert field in doc.metadata, f"Missing metadata field: {field}"
    
    def test_date_parsing(self):
        """Test proper date parsing in metadata."""
        self.exporter._users_cache = {}
        self.exporter._topics_cache = {}
        
        raw_data = [{
            "doc_file": "/backup/doc1.md",
            "meta_file": "/backup/doc1.json",
            "content": self.sample_content,
            "metadata": self.sample_metadata
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        doc = results[0]
        
        # Check that dates are properly parsed
        assert doc.metadata['updated_at'] is not None
        assert doc.metadata['created_at'] is not None
        assert doc.metadata['ingestion_timestamp'] is not None