"""
Tests for BitbucketExporter class.

This module contains comprehensive tests for the BitbucketExporter implementation,
including unit tests for export and process methods, error handling, and integration tests.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Iterator

from langchain_core.documents import Document

from prefect_data_getters.exporters.bitbucket_exporter import BitbucketExporter
from prefect_data_getters.exporters.base import BaseExporter


class TestBitbucketExporter:
    """Test cases for BitbucketExporter class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.exporter = BitbucketExporter()
        
        # Sample test data
        self.sample_pr_data = {
            'id': 123,
            'title': 'Test Pull Request',
            'description': 'This is a test PR description',
            'state': 'OPEN',
            'created_on': '2023-01-10T09:00:00Z',
            'updated_on': '2023-01-15T10:30:00Z',
            'author': {
                'display_name': 'John Doe'
            },
            'participants': [
                {'role': 'REVIEWER', 'user': {'display_name': 'Jane Smith'}},
                {'role': 'PARTICIPANT', 'user': {'display_name': 'Bob Wilson'}}
            ],
            'source': {
                'branch': {'name': 'feature/test-branch'}
            },
            'destination': {
                'branch': {'name': 'main'}
            }
        }
        
        self.sample_comments = [
            {
                'user': {'display_name': 'Jane Smith'},
                'content': {'raw': 'This looks good to me!'}
            },
            {
                'user': {'display_name': 'Bob Wilson'},
                'content': {'raw': 'Please fix the formatting.'}
            }
        ]
        
        self.sample_commits = [
            {
                'author': {
                    'user': {'display_name': 'John Doe'}
                },
                'message': 'Initial implementation'
            },
            {
                'author': {
                    'raw': 'John Doe <john@example.com>'
                },
                'message': 'Fix bug in validation'
            }
        ]
    
    def test_inheritance(self):
        """Test that BitbucketExporter properly inherits from BaseExporter."""
        assert isinstance(self.exporter, BaseExporter)
        assert hasattr(self.exporter, 'export')
        assert hasattr(self.exporter, 'process')
        assert hasattr(self.exporter, 'export_documents')
    
    def test_initialization_default_config(self):
        """Test BitbucketExporter initialization with default configuration."""
        exporter = BitbucketExporter()
        assert exporter._bitbucket_client is None
        assert exporter._workspace_name == "omnidiandevelopmentteam"
    
    def test_initialization_custom_config(self):
        """Test BitbucketExporter initialization with custom configuration."""
        config = {
            "workspace_name": "custom-workspace",
            "max_retries": 5,
            "retry_delay": 3
        }
        exporter = BitbucketExporter(config)
        assert exporter._workspace_name == "custom-workspace"
        assert exporter._get_config("max_retries") == 5
        assert exporter._get_config("retry_delay") == 3
    
    @patch('prefect_data_getters.exporters.jira.get_bitbucket_client')
    def test_export_success(self, mock_get_client):
        """Test successful export of Bitbucket pull requests."""
        # Setup mock client structure
        mock_client = Mock()
        mock_workspace = Mock()
        mock_project = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        
        # Configure mock data
        mock_project.data = {'key': 'TEST'}
        mock_repo.data = {'slug': 'test-repo'}
        mock_pr.data = self.sample_pr_data
        
        # Setup mock comments and commits
        mock_comment = Mock()
        mock_comment.data = self.sample_comments[0]
        mock_pr.comments.return_value = [mock_comment]
        
        mock_commit = Mock()
        mock_commit.data = self.sample_commits[0]
        mock_pr.commits = [mock_commit]
        
        # Configure mock hierarchy
        mock_client.workspaces.get.return_value = mock_workspace
        mock_workspace.projects.each.return_value = [mock_project]
        mock_project.repositories.each.return_value = [mock_repo]
        mock_repo.pullrequests.each.return_value = [mock_pr]
        
        mock_get_client.return_value = mock_client
        
        # Test export
        results = list(self.exporter.export())
        
        assert len(results) == 1
        result = results[0]
        assert result['pr_data'] == self.sample_pr_data
        assert result['workspace'] == "omnidiandevelopmentteam"
        assert result['project_key'] == 'TEST'
        assert result['repo_slug'] == 'test-repo'
        assert len(result['comments']) == 1
        assert len(result['commits']) == 1
    
    @patch('prefect_data_getters.exporters.jira.get_bitbucket_client')
    def test_export_with_filters(self, mock_get_client):
        """Test export with repository and project filters."""
        # Setup mock client
        mock_client = Mock()
        mock_workspace = Mock()
        mock_project = Mock()
        mock_repo = Mock()
        
        mock_project.data = {'key': 'TEST'}
        mock_repo.data = {'slug': 'test-repo'}
        
        mock_client.workspaces.get.return_value = mock_workspace
        mock_workspace.projects.each.return_value = [mock_project]
        mock_project.repositories.each.return_value = [mock_repo]
        mock_repo.pullrequests.each.return_value = []
        
        mock_get_client.return_value = mock_client
        
        # Test with filters
        results = list(self.exporter.export(
            repository='test-repo',
            project_key='TEST',
            state='OPEN',
            days_ago=7
        ))
        
        # Verify filters were applied
        mock_repo.pullrequests.each.assert_called_once()
        call_args = mock_repo.pullrequests.each.call_args
        assert 'q' in call_args[1] or 'q' in (call_args[0] if call_args[0] else {})
        assert 'state' in call_args[1] or 'state' in (call_args[0] if call_args[0] else {})
    
    @patch('prefect_data_getters.exporters.jira.get_bitbucket_client')
    def test_export_error_handling(self, mock_get_client):
        """Test error handling during export."""
        # Setup mock that raises exception
        mock_client = Mock()
        mock_workspace = Mock()
        mock_project = Mock()
        
        mock_project.data = {'key': 'TEST'}
        mock_project.repositories.each.side_effect = Exception("API Error")
        
        mock_client.workspaces.get.return_value = mock_workspace
        mock_workspace.projects.each.return_value = [mock_project]
        
        mock_get_client.return_value = mock_client
        
        # Should handle errors gracefully
        results = list(self.exporter.export())
        assert len(results) == 0
    
    def test_process_success(self):
        """Test successful processing of raw Bitbucket data."""
        raw_data = [{
            "pr_data": self.sample_pr_data,
            "workspace": "test-workspace",
            "project_key": "TEST",
            "repo_slug": "test-repo",
            "comments": self.sample_comments,
            "commits": self.sample_commits
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        
        assert len(results) == 1
        doc = results[0]
        assert isinstance(doc, Document)
        assert doc.id == "123"
        assert "Test Pull Request" in doc.page_content
        assert "This is a test PR description" in doc.page_content
        assert "Comments" in doc.page_content
        assert "Commits" in doc.page_content
        
        # Check metadata
        assert doc.metadata['id'] == "123"
        assert doc.metadata['title'] == "Test Pull Request"
        assert doc.metadata['author_name'] == "John Doe"
        assert doc.metadata['state'] == "OPEN"
        assert doc.metadata['source_branch'] == "feature/test-branch"
        assert doc.metadata['destination_branch'] == "main"
        assert "Jane Smith" in doc.metadata['reviewers']
        assert "John Doe" in doc.metadata['all_participants']
    
    def test_process_minimal_data(self):
        """Test processing with minimal PR data."""
        minimal_pr_data = {
            'id': 456,
            'title': 'Minimal PR',
            'state': 'MERGED'
        }
        
        raw_data = [{
            "pr_data": minimal_pr_data,
            "workspace": "test-workspace",
            "project_key": "TEST",
            "repo_slug": "test-repo",
            "comments": [],
            "commits": []
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        
        assert len(results) == 1
        doc = results[0]
        assert doc.id == "456"
        assert doc.metadata['title'] == "Minimal PR"
        assert doc.metadata['state'] == "MERGED"
        assert doc.metadata['author_name'] == "Unknown"  # Default value
    
    def test_process_error_handling(self):
        """Test error handling during processing."""
        # Invalid data that will cause errors
        raw_data = [
            {"invalid": "data"},  # Missing required fields
            {
                "pr_data": self.sample_pr_data,
                "workspace": "test-workspace",
                "project_key": "TEST",
                "repo_slug": "test-repo",
                "comments": self.sample_comments,
                "commits": self.sample_commits
            }
        ]
        
        results = list(self.exporter.process(iter(raw_data)))
        
        # Should process only the valid item
        assert len(results) == 1
        assert results[0].id == "123"
    
    def test_export_documents_convenience_method(self):
        """Test the convenience method that combines export and process."""
        with patch.object(self.exporter, 'export') as mock_export, \
             patch.object(self.exporter, 'process') as mock_process:
            
            mock_export.return_value = iter([{"test": "data"}])
            mock_process.return_value = iter([Document(page_content="test")])
            
            results = list(self.exporter.export_documents())
            
            assert len(results) == 1
            mock_export.assert_called_once()
            mock_process.assert_called_once()
    
    @patch('prefect_data_getters.exporters.jira.get_bitbucket_client')
    def test_get_bitbucket_client_caching(self, mock_get_client):
        """Test that Bitbucket client is cached properly."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # First call should create client
        client1 = self.exporter._get_bitbucket_client()
        assert client1 == mock_client
        assert mock_get_client.call_count == 1
        
        # Second call should use cached client
        client2 = self.exporter._get_bitbucket_client()
        assert client2 == mock_client
        assert mock_get_client.call_count == 1  # No additional calls
    
    @patch('prefect_data_getters.exporters.jira.get_bitbucket_client')
    def test_get_bitbucket_client_error(self, mock_get_client):
        """Test error handling in client authentication."""
        mock_get_client.side_effect = Exception("Auth failed")
        
        with pytest.raises(Exception):
            self.exporter._get_bitbucket_client()
    
    @patch('prefect_data_getters.exporters.jira.get_bitbucket_client')
    def test_get_repositories(self, mock_get_client):
        """Test getting list of repositories."""
        # Setup mock client structure
        mock_client = Mock()
        mock_workspace = Mock()
        mock_project = Mock()
        mock_repo = Mock()
        
        mock_project.data = {'key': 'TEST'}
        mock_repo.data = {
            'slug': 'test-repo',
            'name': 'Test Repository',
            'full_name': 'test-workspace/test-repo'
        }
        
        mock_client.workspaces.get.return_value = mock_workspace
        mock_workspace.projects.each.return_value = [mock_project]
        mock_project.repositories.each.return_value = [mock_repo]
        
        mock_get_client.return_value = mock_client
        
        repositories = self.exporter.get_repositories()
        
        assert len(repositories) == 1
        repo = repositories[0]
        assert repo['project_key'] == 'TEST'
        assert repo['repo_slug'] == 'test-repo'
        assert repo['repo_name'] == 'Test Repository'
        assert repo['repo_full_name'] == 'test-workspace/test-repo'
    
    @patch('prefect_data_getters.exporters.jira.get_bitbucket_client')
    def test_get_repositories_with_filter(self, mock_get_client):
        """Test getting repositories with project filter."""
        # Setup mock client structure
        mock_client = Mock()
        mock_workspace = Mock()
        mock_project1 = Mock()
        mock_project2 = Mock()
        mock_repo = Mock()
        
        mock_project1.data = {'key': 'TEST1'}
        mock_project2.data = {'key': 'TEST2'}
        mock_repo.data = {
            'slug': 'test-repo',
            'name': 'Test Repository',
            'full_name': 'test-workspace/test-repo'
        }
        
        mock_client.workspaces.get.return_value = mock_workspace
        mock_workspace.projects.each.return_value = [mock_project1, mock_project2]
        mock_project1.repositories.each.return_value = [mock_repo]
        mock_project2.repositories.each.return_value = []
        
        mock_get_client.return_value = mock_client
        
        repositories = self.exporter.get_repositories(project_key='TEST1')
        
        assert len(repositories) == 1
        assert repositories[0]['project_key'] == 'TEST1'
    
    @patch('prefect_data_getters.exporters.jira.get_bitbucket_client')
    def test_get_projects(self, mock_get_client):
        """Test getting list of projects."""
        # Setup mock client structure
        mock_client = Mock()
        mock_workspace = Mock()
        mock_project = Mock()
        
        mock_project.data = {
            'key': 'TEST',
            'name': 'Test Project',
            'description': 'A test project'
        }
        
        mock_client.workspaces.get.return_value = mock_workspace
        mock_workspace.projects.each.return_value = [mock_project]
        
        mock_get_client.return_value = mock_client
        
        projects = self.exporter.get_projects()
        
        assert len(projects) == 1
        project = projects[0]
        assert project['key'] == 'TEST'
        assert project['name'] == 'Test Project'
        assert project['description'] == 'A test project'
    
    def test_date_filtering_logic(self):
        """Test date filtering query construction."""
        # Test with days_ago > 0
        with patch.object(self.exporter, '_get_bitbucket_client') as mock_client_method:
            mock_client = Mock()
            mock_workspace = Mock()
            mock_workspace.projects.each.return_value = []
            mock_client.workspaces.get.return_value = mock_workspace
            mock_client_method.return_value = mock_client
            
            list(self.exporter.export(days_ago=7))
            
            # Should have been called (even with empty results)
            mock_client.workspaces.get.assert_called_once()
    
    def test_participant_processing(self):
        """Test processing of PR participants and roles."""
        pr_data_with_participants = self.sample_pr_data.copy()
        pr_data_with_participants['participants'] = [
            {'role': 'REVIEWER', 'user': {'display_name': 'Reviewer One'}},
            {'role': 'REVIEWER', 'user': {'display_name': 'Reviewer Two'}},
            {'role': 'PARTICIPANT', 'user': {'display_name': 'Participant One'}}
        ]
        
        raw_data = [{
            "pr_data": pr_data_with_participants,
            "workspace": "test-workspace",
            "project_key": "TEST",
            "repo_slug": "test-repo",
            "comments": [],
            "commits": []
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        doc = results[0]
        
        # Check reviewers (only REVIEWER role)
        reviewers = doc.metadata['reviewers']
        assert "Reviewer One" in reviewers
        assert "Reviewer Two" in reviewers
        assert "Participant One" not in reviewers
        
        # Check all participants (includes everyone)
        all_participants = doc.metadata['all_participants']
        assert "John Doe" in all_participants  # Author
        assert "Reviewer One" in all_participants
        assert "Reviewer Two" in all_participants
        assert "Participant One" in all_participants
    
    def test_commit_author_processing(self):
        """Test processing of commit authors with different formats."""
        commits_with_different_formats = [
            {
                'author': {
                    'user': {'display_name': 'User Display Name'}
                },
                'message': 'Commit with user display name'
            },
            {
                'author': {
                    'raw': 'Raw Author <raw@example.com>'
                },
                'message': 'Commit with raw author'
            },
            {
                'author': {},
                'message': 'Commit with no author info'
            }
        ]
        
        raw_data = [{
            "pr_data": self.sample_pr_data,
            "workspace": "test-workspace",
            "project_key": "TEST",
            "repo_slug": "test-repo",
            "comments": [],
            "commits": commits_with_different_formats
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        doc = results[0]
        
        commit_authors = doc.metadata['commit_authors']
        assert "User Display Name" in commit_authors
        assert "Raw Author <raw@example.com>" in commit_authors
        assert "Unknown" in commit_authors
    
    def test_metadata_completeness(self):
        """Test that all expected metadata fields are present."""
        raw_data = [{
            "pr_data": self.sample_pr_data,
            "workspace": "test-workspace",
            "project_key": "TEST",
            "repo_slug": "test-repo",
            "comments": self.sample_comments,
            "commits": self.sample_commits
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        doc = results[0]
        
        expected_fields = [
            'id', 'workspace', 'project_key', 'repo_slug', 'title',
            'author_name', 'state', 'reviewers', 'source_branch',
            'destination_branch', 'all_participants', 'commit_authors',
            'source', 'type', 'ingestion_timestamp', 'created_on', 'updated_on'
        ]
        
        for field in expected_fields:
            assert field in doc.metadata, f"Missing metadata field: {field}"
    
    def test_content_structure(self):
        """Test the structure of generated document content."""
        raw_data = [{
            "pr_data": self.sample_pr_data,
            "workspace": "test-workspace",
            "project_key": "TEST",
            "repo_slug": "test-repo",
            "comments": self.sample_comments,
            "commits": self.sample_commits
        }]
        
        results = list(self.exporter.process(iter(raw_data)))
        doc = results[0]
        
        content = doc.page_content
        
        # Check main sections are present
        assert "Test Pull Request" in content
        assert "This is a test PR description" in content
        assert "########## Comments ##########" in content
        assert "########## Commits ##########" in content
        
        # Check comment content
        assert "Jane Smith: This looks good to me!" in content
        assert "Bob Wilson: Please fix the formatting." in content
        
        # Check commit content
        assert "John Doe: Initial implementation" in content
        assert "Fix bug in validation" in content