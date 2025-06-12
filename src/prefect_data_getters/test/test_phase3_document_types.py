import pytest
from prefect_data_getters.stores.document_types.jira_document import JiraDocument
from prefect_data_getters.stores.document_types.email_document import EmailDocument
from prefect_data_getters.stores.document_types.slack_document import SlackMessageDocument
from prefect_data_getters.stores.document_types.slab_document import SlabDocument, SlabChunkDocument
from prefect_data_getters.stores.document_types.bitbucket_document import BitbucketPR
from prefect_data_getters.stores.document_registry import DocumentTypeRegistry

class TestPhase3DocumentTypes:
    """Test suite for Phase 3 document type refactoring"""
    
    def test_jira_document_properties(self):
        """Test JiraDocument specific properties and functionality"""
        metadata = {
            "key": "PROJ-123",
            "issuetype_name": "Bug",
            "status_name": "Open",
            "priority_name": "High",
            "assignee_name": "John Doe",
            "reporter_name": "Jane Smith",
            "created": "2023-01-01T00:00:00Z",
            "updated": "2023-01-02T00:00:00Z",
            "resolutiondate": "2023-01-03T00:00:00Z"
        }
        
        doc = JiraDocument("Jira issue content", metadata)
        
        assert doc.document_type == "JiraDocument"
        assert doc.jira_key == "PROJ-123"
        assert doc.issue_type == "Bug"
        assert doc.status == "Open"
        assert doc.priority == "High"
        assert doc.assignee == "John Doe"
        assert doc.reporter == "Jane Smith"
        assert doc.get_display_id() == "PROJ-123"
        
        # Test string representation
        str_repr = str(doc)
        assert "Document Type: JiraDocument" in str_repr
        assert "Jira Key: PROJ-123" in str_repr
        assert "Issue Type: Bug" in str_repr
    
    def test_email_document_properties(self):
        """Test EmailDocument specific properties and functionality"""
        metadata = {
            "message-id": "msg-123",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "subject": "Test Email",
            "date": "2023-01-01T00:00:00Z",
            "cc": "cc@example.com"
        }
        
        doc = EmailDocument("Email content", metadata)
        
        assert doc.document_type == "EmailDocument"
        assert doc.message_id == "msg-123"
        assert doc.sender == "sender@example.com"
        assert doc.recipients == "recipient@example.com"
        assert doc.subject == "Test Email"
        assert doc.get_display_id() == "msg-123"
    
    def test_slack_document_properties(self):
        """Test SlackMessageDocument specific properties and functionality"""
        metadata = {
            "user": "john.doe",
            "channel": "general",
            "ts": "1640995200.000000",  # Unix timestamp
            "thread_ts": "1640995100.000000"
        }
        
        doc = SlackMessageDocument("Slack message content", metadata)
        
        assert doc.document_type == "SlackMessageDocument"
        assert doc.user == "john.doe"
        assert doc.channel == "general"
        assert doc.timestamp == "1640995200.000000"
        assert doc.is_thread_reply == True
        assert doc.get_display_id() == "general_1640995200.000000"
        
        # Test formatted timestamp
        assert "2021-12-31" in doc.formatted_timestamp
    
    def test_slab_document_properties(self):
        """Test SlabDocument specific properties and functionality"""
        metadata = {
            "document_id": "slab-123",
            "title": "Test Document",
            "owner": "John Doe",
            "contributors": "Jane Smith, Bob Johnson",
            "topics": "engineering, documentation",
            "type": "specification"
        }
        
        doc = SlabDocument("Slab document content", metadata)
        
        assert doc.document_type == "SlabDocument"
        assert doc.document_id == "slab-123"
        assert doc.title == "Test Document"
        assert doc.owner == "John Doe"
        assert doc.doc_type == "specification"
        assert doc.get_display_id() == "slab-123"
    
    def test_slab_chunk_document_properties(self):
        """Test SlabChunkDocument specific properties and functionality"""
        metadata = {
            "document_id": "slab-123",
            "title": "Test Document",
            "owner": "John Doe"
        }
        
        doc = SlabChunkDocument("Slab chunk content", metadata)
        
        assert doc.document_type == "SlabChunkDocument"
        assert doc.parent_document_id == "slab-123"
        assert doc.doc_type == "slab_chunk"
        assert doc.get_display_id() != "Unknown"  # Should have generated UUID
        assert len(doc.get_display_id()) == 36  # UUID length
    
    def test_bitbucket_pr_properties(self):
        """Test BitbucketPR specific properties and functionality"""
        metadata = {
            "id": "pr-123",
            "repo_slug": "my-repo",
            "title": "Fix bug in authentication",
            "author_name": "John Doe",
            "source_branch": "feature/auth-fix",
            "destination_branch": "main",
            "state": "OPEN",
            "created_on": "2023-01-01T00:00:00Z"
        }
        
        doc = BitbucketPR("PR description content", metadata)
        
        assert doc.document_type == "BitbucketPR"
        assert doc.pr_id == "pr-123"
        assert doc.repository == "my-repo"
        assert doc.title == "Fix bug in authentication"
        assert doc.author == "John Doe"
        assert doc.state == "OPEN"
        assert doc.get_display_id() == "pr-123"
    
    def test_document_registry_integration(self):
        """Test that all document types are properly registered"""
        # Import the package to trigger registration
        import prefect_data_getters.stores.document_types
        
        registered_types = DocumentTypeRegistry.list_registered_types()
        
        assert "jira_issues" in registered_types
        assert "email_messages" in registered_types
        assert "slack_messages" in registered_types
        assert "slab_documents" in registered_types
        assert "slab_document_chunks" in registered_types
        assert "bitbucket_pull_requests" in registered_types
        
        # Test document creation through registry
        jira_data = {
            'page_content': 'test content',
            'metadata': {'key': 'TEST-123'},
            'id': 'TEST-123'
        }
        
        doc = DocumentTypeRegistry.create_document(jira_data, "jira_issues")
        assert isinstance(doc, JiraDocument)
        assert doc.jira_key == "TEST-123"
    
    def test_all_document_types_inherit_from_new_base(self):
        """Test that all document types inherit from the new AIDocument base class"""
        from ..stores.documents_new import AIDocument
        
        # Test with minimal metadata
        jira_doc = JiraDocument("content", {"key": "TEST-1"})
        email_doc = EmailDocument("content", {"message-id": "msg-1"})
        slack_doc = SlackMessageDocument("content", {"user": "test", "channel": "general", "ts": "123"})
        slab_doc = SlabDocument("content", {"document_id": "doc-1"})
        chunk_doc = SlabChunkDocument("content", {"document_id": "doc-1"})
        bb_doc = BitbucketPR("content", {"id": "pr-1"})
        
        # All should inherit from new AIDocument
        assert isinstance(jira_doc, AIDocument)
        assert isinstance(email_doc, AIDocument)
        assert isinstance(slack_doc, AIDocument)
        assert isinstance(slab_doc, AIDocument)
        assert isinstance(chunk_doc, AIDocument)
        assert isinstance(bb_doc, AIDocument)
        
        # All should have document_type property based on class name
        assert jira_doc.document_type == "JiraDocument"
        assert email_doc.document_type == "EmailDocument"
        assert slack_doc.document_type == "SlackMessageDocument"
        assert slab_doc.document_type == "SlabDocument"
        assert chunk_doc.document_type == "SlabChunkDocument"
        assert bb_doc.document_type == "BitbucketPR"
    
    def test_string_representations_use_formatter(self):
        """Test that all document types use the base formatter for consistent output"""
        # Create documents with test data
        jira_doc = JiraDocument("content", {"key": "TEST-1", "issuetype_name": "Bug"})
        email_doc = EmailDocument("content", {"message-id": "msg-1", "from": "test@example.com"})
        slack_doc = SlackMessageDocument("content", {"user": "testuser", "channel": "general"})
        
        # All should have consistent formatting structure
        jira_str = str(jira_doc)
        email_str = str(email_doc)
        slack_str = str(slack_doc)
        
        # All should contain document type
        assert "Document Type:" in jira_str
        assert "Document Type:" in email_str
        assert "Document Type:" in slack_str
        
        # All should contain content section
        assert "Content:" in jira_str
        assert "Content:" in email_str
        assert "Content:" in slack_str
    
    def test_properties_provide_safe_metadata_access(self):
        """Test that properties handle missing metadata gracefully"""
        # Create documents with minimal metadata
        jira_doc = JiraDocument("content", {})
        email_doc = EmailDocument("content", {})
        slack_doc = SlackMessageDocument("content", {})
        
        # Properties should return empty strings for missing metadata
        assert jira_doc.jira_key == ""
        assert jira_doc.issue_type == ""
        assert jira_doc.status == ""
        
        assert email_doc.message_id == ""
        assert email_doc.sender == ""
        assert email_doc.subject == ""
        
        assert slack_doc.user == ""
        assert slack_doc.channel == ""
        assert slack_doc.timestamp == ""
        
        # get_display_id should handle missing data
        assert jira_doc.get_display_id() == "Unknown"
        assert email_doc.get_display_id() == "Unknown"
        assert slack_doc.get_display_id() == "Unknown"