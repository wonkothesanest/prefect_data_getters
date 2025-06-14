"""
Tests for Gmail exporter functionality.

This module contains comprehensive tests for the GmailExporter class,
including authentication, message processing, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import os
import pickle
from datetime import datetime, timedelta
from email.message import EmailMessage

from langchain_core.documents import Document

from prefect_data_getters.exporters.gmail_exporter import GmailExporter


class TestGmailExporter:
    """Test cases for GmailExporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "token_path": "test_token.pickle",
            "credentials_path": "test_creds.json",
            "oauth_port": 8080
        }
        self.exporter = GmailExporter(self.config)
    
    def test_init_default_config(self):
        """Test initialization with default configuration."""
        exporter = GmailExporter()
        
        assert exporter.config["token_path"] == "secrets/gmail_token.pickle"
        assert exporter.config["credentials_path"] == "secrets/google_app_creds.json"
        assert exporter.config["oauth_port"] == 8080
        assert exporter._service is None
        assert exporter._label_mapping is None
    
    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            "token_path": "custom_token.pickle",
            "credentials_path": "custom_creds.json",
            "oauth_port": 9090
        }
        exporter = GmailExporter(config)
        
        assert exporter.config["token_path"] == "custom_token.pickle"
        assert exporter.config["credentials_path"] == "custom_creds.json"
        assert exporter.config["oauth_port"] == 9090
    
    def test_build_default_query(self):
        """Test building default Gmail search query."""
        days_ago = 7
        query = self.exporter._build_default_query(days_ago)
        
        expected_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y/%m/%d')
        
        assert f"after:{expected_date}" in query
        assert "NOT label:useless" in query
        assert "NOT label:not-important" in query
        assert "NOT in:spam" in query
        assert "NOT in:trash" in query
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    def test_authenticate_existing_valid_credentials(self, mock_pickle_load, mock_file, mock_exists):
        """Test authentication with existing valid credentials."""
        # Mock valid credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_pickle_load.return_value = mock_creds
        mock_exists.return_value = True
        
        result = self.exporter._authenticate()
        
        assert result == mock_creds
        mock_exists.assert_called_with("test_token.pickle")
        mock_file.assert_called_with("test_token.pickle", "rb")
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    @patch('google.auth.transport.requests.Request')
    def test_authenticate_refresh_expired_credentials(self, mock_request, mock_pickle_load, mock_file, mock_exists):
        """Test authentication with expired credentials that can be refreshed."""
        # Mock expired credentials with refresh token
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_pickle_load.return_value = mock_creds
        mock_exists.return_value = True
        
        # Mock successful refresh
        def refresh_side_effect(request):
            mock_creds.valid = True
        
        mock_creds.refresh.side_effect = refresh_side_effect
        
        result = self.exporter._authenticate()
        
        assert result == mock_creds
        mock_creds.refresh.assert_called_once()
    
    @patch('os.path.exists')
    @patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file')
    def test_authenticate_new_credentials(self, mock_flow_class, mock_exists):
        """Test authentication when no valid credentials exist."""
        # Mock no existing token file, but credentials file exists
        def exists_side_effect(path):
            return path == "test_creds.json"
        
        mock_exists.side_effect = exists_side_effect
        
        # Mock OAuth flow
        mock_flow = Mock()
        mock_creds = Mock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_class.return_value = mock_flow
        
        with patch('builtins.open', mock_open()):
            with patch('pickle.dump'):
                with patch('os.makedirs'):
                    result = self.exporter._authenticate()
        
        assert result == mock_creds
        mock_flow_class.assert_called_with("test_creds.json", GmailExporter.SCOPES)
        mock_flow.run_local_server.assert_called_with(port=8080, access_type='offline')
    
    @patch('os.path.exists')
    def test_authenticate_missing_credentials_file(self, mock_exists):
        """Test authentication when credentials file is missing."""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError, match="Credentials file not found"):
            self.exporter._authenticate()
    
    @patch.object(GmailExporter, '_authenticate')
    @patch('prefect_data_getters.exporters.gmail_exporter.build')
    def test_get_gmail_service(self, mock_build, mock_authenticate):
        """Test getting Gmail service instance."""
        mock_creds = Mock()
        mock_authenticate.return_value = mock_creds
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = self.exporter._get_gmail_service()
        
        assert result == mock_service
        assert self.exporter._service == mock_service
        mock_build.assert_called_with('gmail', 'v1', credentials=mock_creds)
    
    def test_get_gmail_service_cached(self):
        """Test that Gmail service is cached after first call."""
        mock_service = Mock()
        self.exporter._service = mock_service
        
        result = self.exporter._get_gmail_service()
        
        assert result == mock_service
    
    def test_extract_email_body_simple(self):
        """Test extracting body from simple email message."""
        message = EmailMessage()
        message.set_content("This is the email body.")
        
        body = self.exporter._extract_email_body(message)
        
        assert body.strip() == "This is the email body."
    
    def test_extract_email_body_multipart(self):
        """Test extracting body from multipart email message."""
        message = EmailMessage()
        message.set_content("This is the plain text part.")
        message.add_attachment(b"attachment data", maintype='application', subtype='pdf', filename='test.pdf')
        
        body = self.exporter._extract_email_body(message)
        
        assert "This is the plain text part." in body
        assert "attachment data" not in body  # Attachments should be skipped
    
    def test_extract_metadata(self):
        """Test extracting metadata from email message."""
        message = EmailMessage()
        message['Message-ID'] = '<test@example.com>'
        message['From'] = 'sender@example.com'
        message['To'] = 'recipient@example.com'
        message['Subject'] = 'Test Subject'
        message['Date'] = 'Mon, 01 Jan 2024 12:00:00 +0000'
        message['Google-ID'] = '12345'
        
        metadata = self.exporter._extract_metadata(message)
        
        assert metadata['message-id'] == '<test@example.com>'
        assert metadata['from'] == 'sender@example.com'
        assert metadata['to'] == 'recipient@example.com'
        assert metadata['subject'] == 'Test Subject'
        assert metadata['google-id'] == '12345'
        assert 'date' in metadata  # Date should be parsed
    
    def test_process_message(self):
        """Test processing email message into Document."""
        message = EmailMessage()
        message.set_content("Email body content")
        message['Message-ID'] = '<test@example.com>'
        message['From'] = 'sender@example.com'
        message['Subject'] = 'Test Subject'
        message['Google-ID'] = '12345'
        
        label_mapping = {'INBOX': 'INBOX', 'IMPORTANT': 'Important'}
        
        document = self.exporter._process_message(message, label_mapping)
        
        assert isinstance(document, Document)
        assert document.page_content.strip() == "Email body content"
        assert document.id == '12345'
        assert document.metadata['from'] == 'sender@example.com'
        assert document.metadata['subject'] == 'Test Subject'
    
    @patch.object(GmailExporter, '_get_gmail_service')
    @patch.object(GmailExporter, '_get_label_mapping')
    @patch.object(GmailExporter, '_fetch_messages')
    def test_export_success(self, mock_fetch, mock_labels, mock_service):
        """Test successful export operation - now returns raw data."""
        # Mock service and labels
        mock_service.return_value = Mock()
        mock_labels.return_value = {'INBOX': 'INBOX'}
        
        # Mock messages
        message1 = EmailMessage()
        message1.set_content("Email 1")
        message1['Google-ID'] = '1'
        
        message2 = EmailMessage()
        message2.set_content("Email 2")
        message2['Google-ID'] = '2'
        
        mock_fetch.return_value = [message1, message2]
        
        # Test export - now returns raw data
        raw_data = list(self.exporter.export(days_ago=7))
        
        assert len(raw_data) == 2
        assert all(isinstance(data, EmailMessage) for data in raw_data)
        assert raw_data[0].get_content().strip() == "Email 1"
        assert raw_data[1].get_content().strip() == "Email 2"
        
        # Test process method
        documents = list(self.exporter.process(iter(raw_data)))
        assert len(documents) == 2
        assert all(isinstance(doc, Document) for doc in documents)
        
        # Test convenience method
        all_documents = list(self.exporter.export_documents(days_ago=7))
        assert len(all_documents) == 2
        assert all(isinstance(doc, Document) for doc in all_documents)
    
    @patch.object(GmailExporter, '_get_gmail_service')
    def test_export_with_custom_query(self, mock_service):
        """Test export with custom query."""
        mock_service.return_value = Mock()
        
        with patch.object(self.exporter, '_get_label_mapping') as mock_labels:
            with patch.object(self.exporter, '_fetch_messages') as mock_fetch:
                mock_labels.return_value = {}
                mock_fetch.return_value = []
                
                list(self.exporter.export(query="from:test@example.com"))
                
                # Verify custom query was used
                mock_fetch.assert_called_once()
                args = mock_fetch.call_args[0]
                assert args[1] == "from:test@example.com"  # query parameter
    
    def test_smoosh_labels_together(self):
        """Test label similarity matching."""
        suggested_labels = ["Data Engineering", "Machine Learning"]
        existing_labels = {
            "label1": "AI/Teams/Data Eng",
            "label2": "AI/Teams/ML Team"
        }
        
        result = self.exporter._smoosh_labels_together(
            suggested_labels, "Teams", existing_labels, threshold=0.5
        )
        
        # Should match similar existing labels
        assert len(result) == 2
        # The exact matching depends on the similarity calculation
    
    @patch.object(GmailExporter, '_get_gmail_service')
    @patch.object(GmailExporter, '_get_label_mapping')
    def test_apply_labels_to_email(self, mock_labels, mock_service):
        """Test applying labels to email."""
        mock_service_instance = Mock()
        mock_service.return_value = mock_service_instance
        
        # Mock existing labels
        mock_labels.return_value = {
            'existing_id': 'AI/Cats/Existing Category'
        }
        
        # Mock label creation
        mock_service_instance.users().labels().create().execute.return_value = {
            'id': 'new_label_id'
        }
        
        # Mock message modification
        mock_service_instance.users().messages().modify().execute.return_value = {}
        
        self.exporter.apply_labels_to_email(
            email_id="12345",
            category_labels=["New Category"],
            team_labels=["Engineering"]
        )
        
        # Verify label creation was attempted
        mock_service_instance.users().labels().create.assert_called()
        
        # Verify message modification was called
        # The actual call includes both existing and new labels
        mock_service_instance.users().messages().modify.assert_called()
        call_args = mock_service_instance.users().messages().modify.call_args
        assert call_args[1]['userId'] == 'me'
        assert call_args[1]['id'] == '12345'
        assert 'addLabelIds' in call_args[1]['body']
        assert 'new_label_id' in call_args[1]['body']['addLabelIds']
    
    def test_get_labels(self):
        """Test getting Gmail labels."""
        mock_service = Mock()
        mock_labels = {'label1': 'INBOX', 'label2': 'Sent'}
        
        with patch.object(self.exporter, '_get_gmail_service', return_value=mock_service):
            with patch.object(self.exporter, '_get_label_mapping', return_value=mock_labels):
                result = self.exporter.get_labels()
                
                assert result == mock_labels
    
    def test_reset_cached_data(self):
        """Test resetting cached data."""
        # Set some cached data
        self.exporter._service = Mock()
        self.exporter._label_mapping = {'test': 'test'}
        
        # Reset
        self.exporter.reset_cached_data()
        
        # Verify data is cleared
        assert self.exporter._service is None
        assert self.exporter._label_mapping is None
    
    @patch.object(GmailExporter, '_get_gmail_service')
    def test_export_handles_message_processing_error(self, mock_service):
        """Test that process continues when individual message processing fails."""
        mock_service.return_value = Mock()
        
        # Create a message that will cause processing error
        bad_message = Mock()
        bad_message.get.return_value = None  # This will cause issues in metadata extraction
        
        good_message = EmailMessage()
        good_message.set_content("Good email")
        good_message['Google-ID'] = '123'
        
        with patch.object(self.exporter, '_get_label_mapping', return_value={}):
            with patch.object(self.exporter, '_fetch_messages', return_value=[bad_message, good_message]):
                # Test export returns raw data (both messages)
                raw_data = list(self.exporter.export())
                assert len(raw_data) == 2  # Both messages returned from export
                
                # Test process handles errors gracefully
                documents = list(self.exporter.process(iter(raw_data)))
                
                # Should get one document (the good one), bad one should be skipped during processing
                assert len(documents) == 1
                assert documents[0].page_content.strip() == "Good email"


class TestGmailExporterIntegration:
    """Integration tests for Gmail exporter."""
    
    def test_export_method_signature(self):
        """Test that export method has the correct signature for IDE completion."""
        exporter = GmailExporter()
        
        # This should not raise any errors - testing method signature
        try:
            # We can't actually call this without authentication, but we can verify the signature
            import inspect
            sig = inspect.signature(exporter.export)
            params = sig.parameters
            
            assert 'days_ago' in params
            assert 'query' in params
            assert 'max_results' in params
            
            # Check default values
            assert params['days_ago'].default == 7
            assert params['query'].default is None
            assert params['max_results'].default is None
            
        except Exception as e:
            pytest.fail(f"Method signature test failed: {e}")
    
    def test_inheritance_from_base_exporter(self):
        """Test that GmailExporter properly inherits from BaseExporter."""
        from prefect_data_getters.exporters.base import BaseExporter
        
        exporter = GmailExporter()
        
        assert isinstance(exporter, BaseExporter)
        assert hasattr(exporter, 'export')
        assert hasattr(exporter, '_handle_authentication_error')
        assert hasattr(exporter, '_handle_api_error')
        assert hasattr(exporter, '_log_export_start')
        assert hasattr(exporter, '_log_export_complete')

    """Test backward compatibility functions."""
    