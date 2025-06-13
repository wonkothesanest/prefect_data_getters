"""
Tests for the SlackExporter class.

This module contains comprehensive tests for the SlackExporter implementation,
including authentication, message fetching, processing, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Iterator

from langchain_core.documents import Document

from prefect_data_getters.exporters.slack_exporter import SlackExporter
from prefect_data_getters.stores.document_types.slack_document import SlackMessageDocument


class TestSlackExporter:
    """Test cases for SlackExporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'token': 'xoxb-test-token',
            'page_size': 100,
            'rate_limit_delay': 0.1,  # Faster for tests
            'max_retries': 2
        }
        self.exporter = SlackExporter(self.config)
    
    def test_init_with_config(self):
        """Test SlackExporter initialization with configuration."""
        assert self.exporter.config['token'] == 'xoxb-test-token'
        assert self.exporter.config['page_size'] == 100
        assert self.exporter.config['rate_limit_delay'] == 0.1
        assert self.exporter.config['max_retries'] == 2
    
    def test_init_with_defaults(self):
        """Test SlackExporter initialization with default values."""
        config = {'token': 'xoxb-test-token'}
        exporter = SlackExporter(config)
        
        assert exporter.config['page_size'] == 1000
        assert exporter.config['rate_limit_delay'] == 1.3
        assert exporter.config['max_retries'] == 3
    
    def test_init_missing_token(self):
        """Test SlackExporter initialization fails without token."""
        with pytest.raises(ValueError, match="missing required configuration keys"):
            SlackExporter({})
    
    @patch('prefect_data_getters.exporters.slack_exporter.Slacker')
    def test_get_slack_client(self, mock_slacker):
        """Test getting authenticated Slack client."""
        # Mock the Slacker instance and auth test
        mock_client = Mock()
        mock_auth_response = Mock()
        mock_auth_response.body = {'team': 'Test Team', 'user': 'test_user'}
        mock_client.auth.test.return_value = mock_auth_response
        mock_slacker.return_value = mock_client
        
        client = self.exporter._get_slack_client()
        
        mock_slacker.assert_called_once_with('xoxb-test-token')
        mock_client.auth.test.assert_called_once()
        assert client == mock_client
        
        # Test caching - should not create new client
        client2 = self.exporter._get_slack_client()
        assert client2 == mock_client
        assert mock_slacker.call_count == 1
    
    @patch('prefect_data_getters.exporters.slack_exporter.Slacker')
    def test_authentication_failure(self, mock_slacker):
        """Test authentication failure handling."""
        mock_client = Mock()
        mock_client.auth.test.side_effect = Exception("Auth failed")
        mock_slacker.return_value = mock_client
        
        with pytest.raises(Exception, match="Slack authentication failed"):
            self.exporter._get_slack_client()
    
    def test_calculate_oldest_timestamp(self):
        """Test oldest timestamp calculation."""
        days_ago = 7
        timestamp = self.exporter._calculate_oldest_timestamp(days_ago)
        
        expected_date = datetime.utcnow() - timedelta(days=days_ago)
        expected_timestamp = expected_date.timestamp()
        
        # Allow for small time differences due to execution time
        assert abs(timestamp - expected_timestamp) < 1.0
    
    @patch('prefect_data_getters.exporters.slack_exporter.sleep')
    def test_get_user_mapping(self, mock_sleep):
        """Test user mapping retrieval."""
        mock_client = Mock()
        
        # Mock users.list response
        mock_users_response = Mock()
        mock_users_response.body = {
            'members': [
                {
                    'id': 'U123',
                    'name': 'john',
                    'profile': {'real_name': 'John Doe'}
                },
                {
                    'id': 'U456',
                    'name': 'jane',
                    'profile': {'real_name': 'Jane Smith'}
                }
            ]
        }
        mock_client.users.list.return_value = mock_users_response
        
        user_mapping = self.exporter._get_user_mapping(mock_client)
        
        assert user_mapping['U123'] == 'John Doe'
        assert user_mapping['U456'] == 'Jane Smith'
        assert user_mapping['unknown'] == 'Unknown'  # Default value
        
        # Test caching
        user_mapping2 = self.exporter._get_user_mapping(mock_client)
        assert user_mapping2 == user_mapping
        assert mock_client.users.list.call_count == 1
    
    @patch('prefect_data_getters.exporters.slack_exporter.sleep')
    def test_get_channel_mapping(self, mock_sleep):
        """Test channel mapping retrieval."""
        mock_client = Mock()
        
        # Mock conversations.list responses
        mock_channels_response = Mock()
        mock_channels_response.body = {
            'channels': [
                {'id': 'C123', 'name': 'general'},
                {'id': 'C456', 'name': 'random'}
            ]
        }
        mock_groups_response = Mock()
        mock_groups_response.body = {
            'channels': [
                {'id': 'G789', 'name': 'private-channel'}
            ]
        }
        
        mock_client.conversations.list.side_effect = [
            mock_channels_response, mock_groups_response
        ]
        
        channel_mapping = self.exporter._get_channel_mapping(mock_client)
        
        assert channel_mapping['C123'] == 'general'
        assert channel_mapping['C456'] == 'random'
        assert channel_mapping['G789'] == 'private-channel'
        
        # Verify both calls were made (public and private channels)
        assert mock_client.conversations.list.call_count == 2
    
    def test_replace_user_mentions(self):
        """Test user mention replacement."""
        text = "Hello <@U123> and <@U456>!"
        user_mapping = {
            'U123': 'John Doe',
            'U456': 'Jane Smith'
        }
        
        result = self.exporter._replace_user_mentions(text, user_mapping)
        
        assert result == "Hello @John Doe and @Jane Smith!"
    
    def test_replace_user_mentions_no_mentions(self):
        """Test user mention replacement with no mentions."""
        text = "Hello everyone!"
        user_mapping = {'U123': 'John Doe'}
        
        result = self.exporter._replace_user_mentions(text, user_mapping)
        
        assert result == "Hello everyone!"
    
    def test_extract_message_metadata(self):
        """Test message metadata extraction."""
        message = {
            'user': 'U123',
            'ts': '1609459200.000100',
            'thread_ts': '1609459100.000000',
            'text': 'Hello world!',
            'blocks': [],  # Should be excluded
            'reactions': [
                {'name': 'thumbsup', 'count': 2},
                {'name': 'heart', 'count': 1}
            ]
        }
        user_mapping = {'U123': 'John Doe'}
        channel_name = 'general'
        
        metadata = self.exporter._extract_message_metadata(
            message, user_mapping, channel_name
        )
        
        assert metadata['type'] == 'slack'
        assert metadata['user'] == 'John Doe'
        assert metadata['channel'] == 'general'
        assert metadata['reaction_count'] == 3
        assert metadata['ts'] == 1609459200.000100
        assert metadata['thread_ts'] == 1609459100.000000
        assert 'ts_datetime' in metadata
        assert 'thread_ts_datetime' in metadata
        assert 'text' not in metadata
        assert 'blocks' not in metadata
    
    def test_process_message(self):
        """Test message processing into Document."""
        message = {
            'user': 'U123',
            'ts': '1609459200.000100',
            'text': 'Hello <@U456>!',
            'channel': 'C123'
        }
        user_mapping = {
            'U123': 'John Doe',
            'U456': 'Jane Smith'
        }
        channel_name = 'general'
        
        document = self.exporter._process_message(
            message, user_mapping, channel_name
        )
        
        assert isinstance(document, SlackMessageDocument)
        assert document.page_content == 'Hello @Jane Smith!'
        assert document.metadata['user'] == 'John Doe'
        assert document.metadata['channel'] == 'general'
        assert document.metadata['type'] == 'slack'
    
    def test_process_message_empty_text(self):
        """Test processing message with empty text returns None."""
        message = {
            'user': 'U123',
            'ts': '1609459200.000100',
            'text': '',
            'channel': 'C123'
        }
        user_mapping = {'U123': 'John Doe'}
        channel_name = 'general'
        
        document = self.exporter._process_message(
            message, user_mapping, channel_name
        )
        
        assert document is None
    
    def test_process_message_no_text(self):
        """Test processing message without text field returns None."""
        message = {
            'user': 'U123',
            'ts': '1609459200.000100',
            'channel': 'C123'
        }
        user_mapping = {'U123': 'John Doe'}
        channel_name = 'general'
        
        document = self.exporter._process_message(
            message, user_mapping, channel_name
        )
        
        assert document is None
    
    @patch('prefect_data_getters.exporters.slack_exporter.sleep')
    def test_fetch_channel_messages(self, mock_sleep):
        """Test fetching messages from a channel."""
        mock_client = Mock()
        
        # Mock conversations.history response
        mock_response = Mock()
        mock_response.body = {
            'messages': [
                {
                    'user': 'U123',
                    'ts': '1609459200.000100',
                    'text': 'Hello world!'
                },
                {
                    'user': 'U456',
                    'ts': '1609459300.000200',
                    'text': 'Hi there!',
                    'thread_ts': '1609459200.000100'  # This should trigger replies fetch
                }
            ],
            'has_more': False
        }
        mock_client.conversations.history.return_value = mock_response
        
        # Mock conversations.replies response for threaded message
        mock_replies_response = Mock()
        mock_replies_response.body = {
            'messages': [
                {
                    'user': 'U456',
                    'ts': '1609459200.000100',
                    'text': 'Original message'
                },
                {
                    'user': 'U123',
                    'ts': '1609459400.000300',
                    'text': 'Reply message'
                }
            ],
            'has_more': False
        }
        mock_client.conversations.replies.return_value = mock_replies_response
        
        messages = self.exporter._fetch_channel_messages(
            mock_client, 'C123', 1609459000.0
        )
        
        # Should have original messages plus replies (minus duplicate thread starter)
        assert len(messages) == 3
        assert messages[0]['text'] == 'Hello world!'
        assert messages[1]['text'] == 'Hi there!'
        assert messages[2]['text'] == 'Reply message'
        
        # Verify API calls
        mock_client.conversations.history.assert_called_once()
        mock_client.conversations.replies.assert_called_once()
    
    @patch('prefect_data_getters.exporters.slack_exporter.sleep')
    def test_fetch_thread_replies(self, mock_sleep):
        """Test fetching thread replies."""
        mock_client = Mock()
        
        mock_response = Mock()
        mock_response.body = {
            'messages': [
                {
                    'user': 'U123',
                    'ts': '1609459200.000100',
                    'text': 'Original thread message'
                },
                {
                    'user': 'U456',
                    'ts': '1609459300.000200',
                    'text': 'First reply'
                },
                {
                    'user': 'U789',
                    'ts': '1609459400.000300',
                    'text': 'Second reply'
                }
            ],
            'has_more': False
        }
        mock_client.conversations.replies.return_value = mock_response
        
        replies = self.exporter._fetch_thread_replies(
            mock_client, 'C123', '1609459200.000100', 1609459000.0
        )
        
        # Should exclude the original thread message
        assert len(replies) == 2
        assert replies[0]['text'] == 'First reply'
        assert replies[1]['text'] == 'Second reply'
    
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_channels_to_process')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._fetch_channel_messages')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_channel_mapping')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_user_mapping')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_slack_client')
    def test_export_integration(self, mock_get_client, mock_get_users, 
                               mock_get_channels, mock_fetch_messages, 
                               mock_get_channels_to_process):
        """Test the complete export process integration."""
        # Setup mocks
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_get_users.return_value = {'U123': 'John Doe'}
        mock_get_channels.return_value = {'C123': 'general'}
        
        mock_get_channels_to_process.return_value = [
            {'id': 'C123', 'name': 'general'}
        ]
        
        mock_fetch_messages.return_value = [
            {
                'user': 'U123',
                'ts': '1609459200.000100',
                'text': 'Hello world!'
            }
        ]
        
        # Execute export - now returns raw data
        raw_data = list(self.exporter.export(channels=['general'], days_ago=7))
        
        # Verify raw data results
        assert len(raw_data) == 1
        assert isinstance(raw_data[0], dict)
        assert raw_data[0]['text'] == 'Hello world!'
        assert raw_data[0]['_channel_name'] == 'general'
        
        # Test process method
        documents = list(self.exporter.process(iter(raw_data)))
        assert len(documents) == 1
        assert isinstance(documents[0], SlackMessageDocument)
        assert documents[0].page_content == 'Hello world!'
        assert documents[0].metadata['user'] == 'John Doe'
        assert documents[0].metadata['channel'] == 'general'
    
    def test_reset_cached_data(self):
        """Test resetting cached data."""
        # Set some cached data
        self.exporter._slack_client = Mock()
        self.exporter._user_mapping = {'U123': 'John Doe'}
        self.exporter._channel_mapping = {'C123': 'general'}
        
        # Reset
        self.exporter.reset_cached_data()
        
        # Verify all cached data is cleared
        assert self.exporter._slack_client is None
        assert self.exporter._user_mapping is None
        assert self.exporter._channel_mapping is None
    
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_slack_client')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_channel_mapping')
    def test_get_channels(self, mock_get_mapping, mock_get_client):
        """Test getting channel mapping."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        expected_mapping = {'C123': 'general', 'C456': 'random'}
        mock_get_mapping.return_value = expected_mapping
        
        result = self.exporter.get_channels()
        
        assert result == expected_mapping
        mock_get_client.assert_called_once()
        mock_get_mapping.assert_called_once_with(mock_client)
    
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_slack_client')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_user_mapping')
    def test_get_users(self, mock_get_mapping, mock_get_client):
        """Test getting user mapping."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        expected_mapping = {'U123': 'John Doe', 'U456': 'Jane Smith'}
        mock_get_mapping.return_value = expected_mapping
        
        result = self.exporter.get_users()
        
        assert result == expected_mapping
        mock_get_client.assert_called_once()
        mock_get_mapping.assert_called_once_with(mock_client)


class TestSlackExporterErrorHandling:
    """Test error handling scenarios for SlackExporter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {'token': 'xoxb-test-token'}
        self.exporter = SlackExporter(self.config)
    
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_slack_client')
    def test_export_handles_client_error(self, mock_get_client):
        """Test export handles client creation errors."""
        mock_get_client.side_effect = Exception("Client creation failed")
        
        with pytest.raises(Exception, match="Client creation failed"):
            list(self.exporter.export())
    
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_channels_to_process')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_channel_mapping')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_user_mapping')
    @patch('prefect_data_getters.exporters.slack_exporter.SlackExporter._get_slack_client')
    def test_export_continues_on_channel_error(self, mock_get_client, mock_get_users,
                                              mock_get_channels, mock_get_channels_to_process):
        """Test export continues processing when one channel fails."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_users.return_value = {'U123': 'John Doe'}
        mock_get_channels.return_value = {'C123': 'general', 'C456': 'random'}
        
        mock_get_channels_to_process.return_value = [
            {'id': 'C123', 'name': 'general'},
            {'id': 'C456', 'name': 'random'}
        ]
        
        # Mock fetch_channel_messages to fail for first channel, succeed for second
        def mock_fetch_side_effect(client, channel_id, oldest_ts, limit):
            if channel_id == 'C123':
                raise Exception("Channel fetch failed")
            return [
                {
                    'user': 'U123',
                    'ts': '1609459200.000100',
                    'text': 'Hello from random!'
                }
            ]
        
        with patch.object(self.exporter, '_fetch_channel_messages',
                         side_effect=mock_fetch_side_effect):
            raw_data = list(self.exporter.export())
        
        # Should still get raw data from the successful channel
        assert len(raw_data) == 1
        assert raw_data[0]['_channel_name'] == 'random'
        assert raw_data[0]['text'] == 'Hello from random!'
        
        # Test process method
        documents = list(self.exporter.process(iter(raw_data)))
        assert len(documents) == 1
        assert documents[0].metadata['channel'] == 'random'
    
    def test_extract_metadata_handles_invalid_timestamps(self):
        """Test metadata extraction handles invalid timestamps gracefully."""
        message = {
            'user': 'U123',
            'ts': 'invalid-timestamp',
            'text': 'Hello world!'
        }
        user_mapping = {'U123': 'John Doe'}
        channel_name = 'general'
        
        # Should not raise exception
        metadata = self.exporter._extract_message_metadata(
            message, user_mapping, channel_name
        )
        
        assert metadata['user'] == 'John Doe'
        assert metadata['channel'] == 'general'
        # Invalid timestamp should be preserved as-is
        assert metadata['ts'] == 'invalid-timestamp'


class TestSlackExporterRateLimiting:
    """Test rate limiting scenarios for SlackExporter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'token': 'xoxb-test-token',
            'rate_limit_delay': 0.1  # Faster for tests
        }
        self.exporter = SlackExporter(self.config)
    
    @patch('prefect_data_getters.exporters.slack_exporter.sleep')
    def test_fetch_messages_handles_rate_limit(self, mock_sleep):
        """Test message fetching handles rate limiting."""
        mock_client = Mock()
        
        # Create a real HTTPError with 429 status
        import requests
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '60'}
        rate_limit_error = requests.exceptions.HTTPError(response=rate_limit_response)
        rate_limit_error.response = rate_limit_response
        
        # First call raises rate limit, second succeeds
        mock_response = Mock()
        mock_response.body = {
            'messages': [
                {
                    'user': 'U123',
                    'ts': '1609459200.000100',
                    'text': 'Hello world!'
                }
            ],
            'has_more': False
        }
        
        mock_client.conversations.history.side_effect = [
            rate_limit_error, mock_response
        ]
        
        messages = self.exporter._fetch_channel_messages(
            mock_client, 'C123', 1609459000.0
        )
        
        # Should eventually succeed and return messages
        assert len(messages) == 1
        assert messages[0]['text'] == 'Hello world!'
        
        # Should have called sleep for rate limiting
        mock_sleep.assert_called()