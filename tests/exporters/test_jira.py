"""
Tests for the Jira exporter implementation.

This module contains comprehensive tests for the JiraExporter class,
including unit tests for export, process, and integration functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Iterator, Dict, Any

from langchain_core.documents import Document

from prefect_data_getters.exporters.jira_exporter import JiraExporter
from prefect_data_getters.exporters.base import BaseExporter


class TestJiraExporter:
    """Test suite for JiraExporter class."""
    
    def test_inheritance(self):
        """Test that JiraExporter properly inherits from BaseExporter."""
        exporter = JiraExporter()
        assert isinstance(exporter, BaseExporter)
        assert hasattr(exporter, 'export')
        assert hasattr(exporter, 'process')
        assert hasattr(exporter, 'export_documents')
    
    def test_initialization_default(self):
        """Test JiraExporter initialization with default parameters."""
        exporter = JiraExporter()
        assert exporter.config == {}
        assert exporter._client is None
        assert exporter.logger is not None
    
    def test_initialization_with_config(self):
        """Test JiraExporter initialization with custom config."""
        config = {
            'username': 'test@example.com',
            'api_token': 'test-token',
            'url': 'https://test.atlassian.net'
        }
        exporter = JiraExporter(config=config)
        assert exporter.config == config
    
    @patch('prefect_data_getters.exporters.jira_exporter.Jira')
    def test_get_jira_client_with_config(self, mock_jira):
        """Test Jira client creation with config credentials."""
        config = {
            'username': 'test@example.com',
            'api_token': 'test-token',
            'url': 'https://test.atlassian.net'
        }
        exporter = JiraExporter(config=config)
        
        mock_client = Mock()
        mock_jira.return_value = mock_client
        
        client = exporter._get_jira_client()
        
        mock_jira.assert_called_once_with(
            url='https://test.atlassian.net',
            username='test@example.com',
            password='test-token'
        )
        assert client == mock_client
        assert exporter._client == mock_client
    
    @patch('prefect_data_getters.exporters.jira_exporter.Secret')
    @patch('prefect_data_getters.exporters.jira_exporter.Jira')
    def test_get_jira_client_with_secret(self, mock_jira, mock_secret):
        """Test Jira client creation with Prefect Secret."""
        # Mock the Secret block
        mock_secret_block = Mock()
        mock_secret_block.get.return_value = {
            'username': 'secret@example.com',
            'api-token': 'secret-token',
            'url': 'https://secret.atlassian.net'
        }
        mock_secret.load.return_value = mock_secret_block
        
        mock_client = Mock()
        mock_jira.return_value = mock_client
        
        exporter = JiraExporter()
        client = exporter._get_jira_client()
        
        mock_secret.load.assert_called_once_with("jira-credentials")
        mock_jira.assert_called_once_with(
            url='https://secret.atlassian.net',
            username='secret@example.com',
            password='secret-token'
        )
        assert client == mock_client
    
    @patch('prefect_data_getters.exporters.jira_exporter.Secret')
    def test_get_jira_client_authentication_failure(self, mock_secret):
        """Test Jira client creation with authentication failure."""
        mock_secret.load.side_effect = Exception("Authentication failed")
        
        exporter = JiraExporter()
        
        with pytest.raises(Exception, match="Authentication failed"):
            exporter._get_jira_client()
    
    def test_export_method_signature(self):
        """Test that export method has the correct signature."""
        exporter = JiraExporter()
        
        # Test that method exists and is callable
        assert callable(exporter.export)
        
        # Test default parameters by inspecting the method
        import inspect
        sig = inspect.signature(exporter.export)
        params = sig.parameters
        
        assert 'project' in params
        assert 'status' in params
        assert 'assignee' in params
        assert 'days_ago' in params
        assert params['days_ago'].default == 30
    
    @patch.object(JiraExporter, '_get_jira_client')
    def test_export_basic_functionality(self, mock_get_client):
        """Test basic export functionality with mocked Jira client."""
        # Mock Jira client and response
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Mock JQL response
        mock_response = {
            'issues': [
                {
                    'key': 'TEST-1',
                    'fields': {
                        'summary': 'Test Issue 1',
                        'description': 'Test Description 1'
                    }
                },
                {
                    'key': 'TEST-2',
                    'fields': {
                        'summary': 'Test Issue 2',
                        'description': 'Test Description 2'
                    }
                }
            ]
        }
        mock_client.jql.return_value = mock_response
        
        exporter = JiraExporter()
        issues = list(exporter.export(projects='TEST', days_ago=7))
        
        assert len(issues) == 2
        assert issues[0]['key'] == 'TEST-1'
        assert issues[1]['key'] == 'TEST-2'
        
        # Verify JQL was called with correct parameters
        mock_client.jql.assert_called_once()
        call_args = mock_client.jql.call_args
        assert 'project = "TEST"' in call_args[0][0]
        assert 'updated >=' in call_args[0][0]
    
    @patch.object(JiraExporter, '_get_jira_client')
    def test_export_with_all_filters(self, mock_get_client):
        """Test export with all filter parameters."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.jql.return_value = {'issues': []}
        
        exporter = JiraExporter()
        list(exporter.export(
            projects='PROJ',
            status='In Progress',
            assignee='john.doe',
            days_ago=14
        ))
        
        # Verify JQL query construction
        call_args = mock_client.jql.call_args[0][0]
        assert 'project = "PROJ"' in call_args
        assert 'status = "In Progress"' in call_args
        assert 'assignee = "john.doe"' in call_args
        assert 'updated >=' in call_args
    
    @patch.object(JiraExporter, '_get_jira_client')
    def test_export_pagination(self, mock_get_client):
        """Test export handles pagination correctly."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Mock paginated responses
        first_response = {
            'issues': [{'key': f'TEST-{i}'} for i in range(1, 51)]  # 50 issues
        }
        second_response = {
            'issues': [{'key': f'TEST-{i}'} for i in range(51, 76)]  # 25 issues
        }
        third_response = {
            'issues': []  # No more issues
        }
        
        mock_client.jql.side_effect = [first_response, second_response, third_response]
        
        exporter = JiraExporter()
        issues = list(exporter.export())
        
        assert len(issues) == 75
        assert mock_client.jql.call_count == 2  # Should stop after second call
    
    @patch.object(JiraExporter, '_get_jira_client')
    def test_export_api_error(self, mock_get_client):
        """Test export handles API errors gracefully."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.jql.side_effect = Exception("API Error")
        
        exporter = JiraExporter()
        
        with pytest.raises(Exception, match="API Error"):
            list(exporter.export())
    
    def test_process_method_signature(self):
        """Test that process method has the correct signature."""
        exporter = JiraExporter()
        
        assert callable(exporter.process)
        
        import inspect
        sig = inspect.signature(exporter.process)
        params = sig.parameters
        
        assert 'raw_data' in params
        assert len(params) == 1  # raw_data (self is not included in signature)
    
    def test_process_basic_functionality(self):
        """Test basic process functionality."""
        exporter = JiraExporter()
        
        # Sample raw issue data
        raw_issues = [
            {
                'key': 'TEST-1',
                'fields': {
                    'summary': 'Test Issue 1',
                    'description': 'Test Description 1',
                    'priority': {'name': 'High'},
                    'status': {'name': 'Open'},
                    'created': '2023-01-01T10:00:00.000+0000',
                    'updated': '2023-01-02T10:00:00.000+0000'
                }
            }
        ]
        
        documents = list(exporter.process(iter(raw_issues)))
        
        assert len(documents) == 1
        doc = documents[0]
        assert isinstance(doc, Document)
        assert doc.id == 'TEST-1'
        assert 'Test Issue 1' in doc.page_content
        assert 'Test Description 1' in doc.page_content
        assert doc.metadata['key'] == 'TEST-1'
        assert doc.metadata['priority_name'] == 'High'
        assert doc.metadata['status_name'] == 'Open'
    
    def test_process_with_comments(self):
        """Test process functionality with comments."""
        exporter = JiraExporter()
        
        raw_issues = [
            {
                'key': 'TEST-1',
                'fields': {
                    'summary': 'Test Issue',
                    'description': 'Test Description',
                    'comment': {
                        'comments': [
                            {
                                'author': {'displayName': 'John Doe'},
                                'body': 'This is a comment'
                            },
                            {
                                'author': {'displayName': 'Jane Smith'},
                                'body': 'This is another comment'
                            }
                        ]
                    }
                }
            }
        ]
        
        documents = list(exporter.process(iter(raw_issues)))
        
        assert len(documents) == 1
        doc = documents[0]
        assert '########## Comments ##########' in doc.page_content
        assert 'John Doe: This is a comment' in doc.page_content
        assert 'Jane Smith: This is another comment' in doc.page_content
    
    def test_process_with_invalid_data(self):
        """Test process handles invalid data gracefully."""
        exporter = JiraExporter()
        
        # Mix of valid and invalid data
        raw_issues = [
            {
                'key': 'TEST-1',
                'fields': {
                    'summary': 'Valid Issue',
                    'description': 'Valid Description'
                }
            },
            {
                # Missing key field - will get empty key
                'fields': {
                    'summary': 'Invalid Issue'
                }
            },
            {
                'key': 'TEST-2',
                'fields': {
                    'summary': 'Another Valid Issue',
                    'description': 'Another Valid Description'
                }
            }
        ]
        
        documents = list(exporter.process(iter(raw_issues)))
        
        # Should process all issues, even those with missing keys (robust processing)
        assert len(documents) == 3
        assert documents[0].id == 'TEST-1'
        assert documents[1].id == ''  # Missing key becomes empty string
        assert documents[2].id == 'TEST-2'
        
        # Verify content is still processed correctly
        assert 'Valid Issue' in documents[0].page_content
        assert 'Invalid Issue' in documents[1].page_content
        assert 'Another Valid Issue' in documents[2].page_content
    
    def test_get_issue_value_simple_path(self):
        """Test _get_issue_value with simple field path."""
        exporter = JiraExporter()
        
        issue = {
            'fields': {
                'summary': 'Test Summary'
            }
        }
        
        value = exporter._get_issue_value(issue, 'fields.summary')
        assert value == 'Test Summary'
    
    def test_get_issue_value_nested_path(self):
        """Test _get_issue_value with nested field path."""
        exporter = JiraExporter()
        
        issue = {
            'fields': {
                'priority': {
                    'name': 'High'
                }
            }
        }
        
        value = exporter._get_issue_value(issue, 'fields.priority.name')
        assert value == 'High'
    
    def test_get_issue_value_missing_field(self):
        """Test _get_issue_value with missing field."""
        exporter = JiraExporter()
        
        issue = {
            'fields': {
                'summary': 'Test Summary'
            }
        }
        
        value = exporter._get_issue_value(issue, 'fields.missing.field')
        assert value is None
    
    def test_get_issue_value_list_access(self):
        """Test _get_issue_value with list access."""
        exporter = JiraExporter()
        
        issue = {
            'fields': {
                'comments': [
                    {'body': 'First comment'},
                    {'body': 'Second comment'}
                ]
            }
        }
        
        value = exporter._get_issue_value(issue, 'fields.comments.0.body')
        assert value == 'First comment'
    
    def test_export_documents_integration(self):
        """Test the export_documents convenience method."""
        with patch.object(JiraExporter, '_get_jira_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.jql.return_value = {
                'issues': [
                    {
                        'key': 'TEST-1',
                        'fields': {
                            'summary': 'Test Issue',
                            'description': 'Test Description'
                        }
                    }
                ]
            }
            
            exporter = JiraExporter()
            documents = list(exporter.export_documents(project='TEST'))
            
            assert len(documents) == 1
            assert isinstance(documents[0], Document)
            assert documents[0].id == 'TEST-1'
    
    def test_format_issue_to_document_complete(self):
        """Test _format_issue_to_document with complete issue data."""
        exporter = JiraExporter()
        
        issue = {
            'key': 'PROJ-123',
            'fields': {
                'summary': 'Test Summary',
                'description': 'Test Description',
                'priority': {'name': 'High'},
                'status': {
                    'name': 'In Progress',
                    'statusCategory': {'name': 'In Progress'}
                },
                'creator': {'displayName': 'John Creator'},
                'reporter': {'displayName': 'Jane Reporter'},
                'assignee': {'displayName': 'Bob Assignee'},
                'issuetype': {
                    'name': 'Bug',
                    'description': 'Bug issue type',
                    'subtask': False,
                    'hierarchyLevel': 0
                },
                'project': {
                    'name': 'Test Project',
                    'key': 'PROJ'
                },
                'created': '2023-01-01T10:00:00.000+0000',
                'updated': '2023-01-02T10:00:00.000+0000',
                'resolutiondate': '2023-01-03T10:00:00.000+0000',
                'watches': {
                    'watchCount': 5,
                    'isWatching': True
                }
            }
        }
        
        document = exporter._format_issue_to_document(issue)
        
        assert document.id == 'PROJ-123'
        assert 'Test Summary' in document.page_content
        assert 'Test Description' in document.page_content
        
        # Check metadata
        metadata = document.metadata
        assert metadata['key'] == 'PROJ-123'
        assert metadata['priority_name'] == 'High'
        assert metadata['status_name'] == 'In Progress'
        assert metadata['creator_displayName'] == 'John Creator'
        assert metadata['reporter_displayName'] == 'Jane Reporter'
        assert metadata['assignee_displayName'] == 'Bob Assignee'
        assert metadata['issuetype_name'] == 'Bug'
        assert metadata['project_name'] == 'Test Project'
        assert metadata['project_key'] == 'PROJ'
        assert 'created_ts' in metadata
        assert 'updated_ts' in metadata
    
    def test_date_parsing_edge_cases(self):
        """Test date parsing with various formats."""
        exporter = JiraExporter()
        
        # Test with Z suffix
        issue_z = {
            'key': 'TEST-1',
            'fields': {
                'summary': 'Test',
                'created': '2023-01-01T10:00:00.000Z'
            }
        }
        
        doc_z = exporter._format_issue_to_document(issue_z)
        assert 'created_ts' in doc_z.metadata
        
        # Test with timezone offset
        issue_tz = {
            'key': 'TEST-2',
            'fields': {
                'summary': 'Test',
                'created': '2023-01-01T10:00:00.000+0000'
            }
        }
        
        doc_tz = exporter._format_issue_to_document(issue_tz)
        assert 'created_ts' in doc_tz.metadata
        
        # Test with invalid date
        issue_invalid = {
            'key': 'TEST-3',
            'fields': {
                'summary': 'Test',
                'created': 'invalid-date'
            }
        }
        
        doc_invalid = exporter._format_issue_to_document(issue_invalid)
        assert doc_invalid.metadata.get('created') == 'invalid-date'
        assert 'created_ts' not in doc_invalid.metadata


# Integration tests
class TestJiraExporterIntegration:
    """Integration tests for JiraExporter."""
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            'username': 'test@example.com',
            'api_token': 'test-token',
            'url': 'https://test.atlassian.net'
        }
    
    def test_full_workflow_mock(self, sample_config):
        """Test complete workflow with mocked dependencies."""
        with patch('prefect_data_getters.exporters.jira_exporter.Jira') as mock_jira:
            mock_client = Mock()
            mock_jira.return_value = mock_client
            mock_client.jql.return_value = {
                'issues': [
                    {
                        'key': 'PROJ-1',
                        'fields': {
                            'summary': 'Integration Test Issue',
                            'description': 'This is a test issue for integration testing',
                            'priority': {'name': 'Medium'},
                            'status': {'name': 'Open'},
                            'created': '2023-01-01T10:00:00.000+0000'
                        }
                    }
                ]
            }
            
            exporter = JiraExporter(config=sample_config)
            
            # Test export
            raw_issues = list(exporter.export(projects='PROJ'))
            assert len(raw_issues) == 1
            assert raw_issues[0]['key'] == 'PROJ-1'
            
            # Test process
            documents = list(exporter.process(iter(raw_issues)))
            assert len(documents) == 1
            assert documents[0].id == 'PROJ-1'
            
            # Test convenience method
            all_docs = list(exporter.export_documents(project='PROJ'))
            assert len(all_docs) == 1
            assert all_docs[0].id == 'PROJ-1'