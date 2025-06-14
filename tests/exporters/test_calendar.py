"""
Tests for CalendarExporter class.

This module contains comprehensive tests for the CalendarExporter implementation,
including unit tests for export and process methods, error handling, and integration tests.
"""

import os
import pickle
import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from datetime import datetime, timedelta
from typing import Iterator

from langchain_core.documents import Document

from prefect_data_getters.exporters.calendar_exporter import CalendarExporter
from prefect_data_getters.exporters.base import BaseExporter


class TestCalendarExporter:
    """Test cases for CalendarExporter class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.exporter = CalendarExporter()
        
        # Sample test data
        self.sample_event = {
            'id': 'event123',
            'summary': 'Team Meeting',
            'description': 'Weekly team sync meeting',
            'location': 'Conference Room A',
            'start': {
                'dateTime': '2023-01-15T10:00:00Z'
            },
            'end': {
                'dateTime': '2023-01-15T11:00:00Z'
            },
            'organizer': {
                'displayName': 'John Doe',
                'email': 'john@example.com'
            },
            'creator': {
                'displayName': 'Jane Smith',
                'email': 'jane@example.com'
            },
            'attendees': [
                {
                    'displayName': 'Alice Johnson',
                    'email': 'alice@example.com'
                },
                {
                    'email': 'bob@example.com'  # No display name
                }
            ],
            'status': 'confirmed',
            'visibility': 'default',
            'eventType': 'default',
            'recurringEventId': 'recurring123'
        }
        
        self.sample_all_day_event = {
            'id': 'allday123',
            'summary': 'Holiday',
            'start': {
                'date': '2023-01-16'
            },
            'end': {
                'date': '2023-01-17'
            }
        }
    
    def test_inheritance(self):
        """Test that CalendarExporter properly inherits from BaseExporter."""
        assert isinstance(self.exporter, BaseExporter)
        assert hasattr(self.exporter, 'export')
        assert hasattr(self.exporter, 'process')
        assert hasattr(self.exporter, 'export_documents')
    
    def test_initialization_default_config(self):
        """Test CalendarExporter initialization with default configuration."""
        exporter = CalendarExporter()
        assert exporter._service is None
        assert exporter._credentials is None
        assert exporter._token_path == "secrets/google_token.pickle"
        assert exporter._credentials_path == "secrets/google_app_creds.json"
    
    def test_initialization_custom_config(self):
        """Test CalendarExporter initialization with custom configuration."""
        config = {
            "token_path": "custom/token.pickle",
            "credentials_path": "custom/creds.json",
            "max_retries": 5,
            "retry_delay": 3
        }
        exporter = CalendarExporter(config)
        assert exporter._token_path == "custom/token.pickle"
        assert exporter._credentials_path == "custom/creds.json"
        assert exporter._get_config("max_retries") == 5
        assert exporter._get_config("retry_delay") == 3
    
    @patch('googleapiclient.discovery.build')
    @patch.object(CalendarExporter, '_authenticate_google_calendar')
    def test_export_success(self, mock_auth, mock_build):
        """Test successful export of calendar events."""
        # Setup mock service
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        
        # Configure mock response
        mock_response = {
            'items': [self.sample_event, self.sample_all_day_event],
            'nextPageToken': None
        }
        mock_list.execute.return_value = mock_response
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        
        mock_build.return_value = mock_service
        mock_auth.return_value = Mock()
        
        # Test export
        results = list(self.exporter.export())
        
        assert len(results) == 2
        assert results[0] == self.sample_event
        assert results[1] == self.sample_all_day_event
        
        # Verify API was called correctly
        mock_events.list.assert_called()
        call_args = mock_events.list.call_args[1]
        assert call_args['calendarId'] == 'primary'
        assert call_args['singleEvents'] is True
        assert call_args['orderBy'] == 'startTime'
        assert 'timeMin' in call_args
        assert 'timeMax' in call_args
    
    @patch('googleapiclient.discovery.build')
    @patch.object(CalendarExporter, '_authenticate_google_calendar')
    def test_export_with_pagination(self, mock_auth, mock_build):
        """Test export with paginated results."""
        # Setup mock service
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        
        # Configure mock responses for pagination
        responses = [
            {
                'items': [self.sample_event],
                'nextPageToken': 'token123'
            },
            {
                'items': [self.sample_all_day_event],
                'nextPageToken': None
            }
        ]
        mock_list.execute.side_effect = responses
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        
        mock_build.return_value = mock_service
        mock_auth.return_value = Mock()
        
        # Test export
        results = list(self.exporter.export())
        
        assert len(results) == 2
        assert mock_list.execute.call_count == 2
    
    @patch('googleapiclient.discovery.build')
    @patch.object(CalendarExporter, '_authenticate_google_calendar')
    def test_export_with_parameters(self, mock_auth, mock_build):
        """Test export with custom parameters."""
        # Setup mock service
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        
        mock_response = {'items': [], 'nextPageToken': None}
        mock_list.execute.return_value = mock_response
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        
        mock_build.return_value = mock_service
        mock_auth.return_value = Mock()
        
        # Test export with custom parameters
        list(self.exporter.export(
            calendar_id='custom@example.com',
            days_ago=14,
            days_ahead=60,
            max_results=100
        ))
        
        # Verify parameters were passed correctly
        call_args = mock_events.list.call_args[1]
        assert call_args['calendarId'] == 'custom@example.com'
        assert call_args['maxResults'] == 100
    
    @patch('googleapiclient.discovery.build')
    @patch.object(CalendarExporter, '_authenticate_google_calendar')
    def test_export_error_handling(self, mock_auth, mock_build):
        """Test error handling during export."""
        # Setup mock service that raises exception
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        
        mock_list.execute.side_effect = Exception("API Error")
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        
        mock_build.return_value = mock_service
        mock_auth.return_value = Mock()
        
        # Should handle errors gracefully
        results = list(self.exporter.export())
        assert len(results) == 0
    
    def test_process_success(self):
        """Test successful processing of raw calendar data."""
        raw_data = [self.sample_event, self.sample_all_day_event]
        
        results = list(self.exporter.process(iter(raw_data)))
        
        assert len(results) == 2
        
        # Test regular event
        doc1 = results[0]
        assert isinstance(doc1, Document)
        assert doc1.id == 'event123'
        assert 'Team Meeting' in doc1.page_content
        assert 'Weekly team sync meeting' in doc1.page_content
        assert 'Conference Room A' in doc1.page_content
        assert 'John Doe' in doc1.page_content
        assert 'Alice Johnson' in doc1.page_content
        
        # Check metadata
        assert doc1.metadata['event_id'] == 'event123'
        assert doc1.metadata['summary'] == 'Team Meeting'
        assert doc1.metadata['description'] == 'Weekly team sync meeting'
        assert doc1.metadata['location'] == 'Conference Room A'
        assert doc1.metadata['organizer'] == 'John Doe'
        assert doc1.metadata['creator'] == 'Jane Smith'
        assert 'Alice Johnson' in doc1.metadata['attendees']
        assert 'bob@example.com' in doc1.metadata['attendees']
        assert doc1.metadata['status'] == 'confirmed'
        assert doc1.metadata['visibility'] == 'default'
        assert doc1.metadata['eventType'] == 'default'
        assert doc1.metadata['recurringEventId'] == 'recurring123'
        assert doc1.metadata['source'] == 'google_calendar'
        assert doc1.metadata['type'] == 'calendar_event'
        
        # Test all-day event
        doc2 = results[1]
        assert doc2.id == 'allday123'
        assert 'Holiday' in doc2.page_content
        assert doc2.metadata['summary'] == 'Holiday'
    
    def test_process_minimal_event(self):
        """Test processing with minimal event data."""
        minimal_event = {
            'id': 'minimal123',
            'summary': 'Simple Event'
        }
        
        results = list(self.exporter.process(iter([minimal_event])))
        
        assert len(results) == 1
        doc = results[0]
        assert doc.id == 'minimal123'
        assert doc.metadata['summary'] == 'Simple Event'
        assert doc.metadata['description'] == ''
        assert doc.metadata['location'] == ''
        assert doc.metadata['organizer'] == ''
        assert doc.metadata['attendees'] == ''
    
    def test_process_error_handling(self):
        """Test error handling during processing."""
        # Invalid data that will cause errors
        raw_data = [
            {"invalid": "data"},  # Missing required fields
            self.sample_event
        ]
        
        results = list(self.exporter.process(iter(raw_data)))
        
        # Should process only the valid item
        assert len(results) == 1
        assert results[0].id == 'event123'
    
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
    
    @patch('googleapiclient.discovery.build')
    @patch.object(CalendarExporter, '_authenticate_google_calendar')
    def test_get_calendar_service_caching(self, mock_auth, mock_build):
        """Test that calendar service is cached properly."""
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_auth.return_value = Mock()
        
        # First call should create service
        service1 = self.exporter._get_calendar_service()
        assert service1 == mock_service
        assert mock_build.call_count == 1
        
        # Second call should use cached service
        service2 = self.exporter._get_calendar_service()
        assert service2 == mock_service
        assert mock_build.call_count == 1  # No additional calls
    
    @patch.object(CalendarExporter, '_authenticate_google_calendar')
    def test_get_calendar_service_error(self, mock_auth):
        """Test error handling in service creation."""
        mock_auth.side_effect = Exception("Auth failed")
        
        with pytest.raises(Exception):
            self.exporter._get_calendar_service()
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    def test_authenticate_existing_valid_credentials(self, mock_pickle_load, mock_file, mock_exists):
        """Test authentication with existing valid credentials."""
        # Setup mock credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_pickle_load.return_value = mock_creds
        mock_exists.return_value = True
        
        result = self.exporter._authenticate_google_calendar()
        
        assert result == mock_creds
        mock_pickle_load.assert_called_once()
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    @patch('pickle.dump')
    @patch('google.auth.transport.requests.Request')
    def test_authenticate_refresh_expired_credentials(self, mock_request, mock_pickle_dump, 
                                                     mock_pickle_load, mock_file, mock_exists):
        """Test authentication with expired credentials that can be refreshed."""
        # Setup mock credentials
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = 'refresh_token'
        mock_pickle_load.return_value = mock_creds
        mock_exists.return_value = True
        
        # Mock successful refresh
        def refresh_side_effect(request):
            mock_creds.valid = True
        
        mock_creds.refresh.side_effect = refresh_side_effect
        
        result = self.exporter._authenticate_google_calendar()
        
        assert result == mock_creds
        mock_creds.refresh.assert_called_once()
        mock_pickle_dump.assert_called_once()
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.dump')
    @patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file')
    def test_authenticate_new_credentials(self, mock_flow_class, mock_pickle_dump, 
                                         mock_file, mock_makedirs, mock_exists):
        """Test authentication with new OAuth flow."""
        # Setup mocks
        mock_exists.side_effect = lambda path: 'google_app_creds.json' in path
        mock_flow = Mock()
        mock_creds = Mock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_class.return_value = mock_flow
        
        result = self.exporter._authenticate_google_calendar()
        
        assert result == mock_creds
        mock_flow.run_local_server.assert_called_once_with(port=8080, access_type='offline')
        mock_pickle_dump.assert_called_once()
    
    @patch('os.path.exists')
    def test_authenticate_missing_credentials_file(self, mock_exists):
        """Test authentication with missing credentials file."""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            self.exporter._authenticate_google_calendar()
    
    @patch('googleapiclient.discovery.build')
    @patch.object(CalendarExporter, '_authenticate_google_calendar')
    def test_get_calendars(self, mock_auth, mock_build):
        """Test getting list of calendars."""
        # Setup mock service
        mock_service = Mock()
        mock_calendar_list = Mock()
        mock_list = Mock()
        
        mock_response = {
            'items': [
                {
                    'id': 'primary',
                    'summary': 'Primary Calendar',
                    'description': 'Main calendar',
                    'primary': True,
                    'accessRole': 'owner'
                },
                {
                    'id': 'secondary@example.com',
                    'summary': 'Secondary Calendar',
                    'primary': False,
                    'accessRole': 'reader'
                }
            ]
        }
        mock_list.execute.return_value = mock_response
        mock_calendar_list.list.return_value = mock_list
        mock_service.calendarList.return_value = mock_calendar_list
        
        mock_build.return_value = mock_service
        mock_auth.return_value = Mock()
        
        calendars = self.exporter.get_calendars()
        
        assert len(calendars) == 2
        assert calendars[0]['id'] == 'primary'
        assert calendars[0]['summary'] == 'Primary Calendar'
        assert calendars[0]['primary'] is True
        assert calendars[1]['id'] == 'secondary@example.com'
        assert calendars[1]['primary'] is False
    
    @patch('googleapiclient.discovery.build')
    @patch.object(CalendarExporter, '_authenticate_google_calendar')
    def test_get_calendars_error(self, mock_auth, mock_build):
        """Test error handling in get_calendars."""
        # Setup mock service that raises exception
        mock_service = Mock()
        mock_calendar_list = Mock()
        mock_list = Mock()
        
        mock_list.execute.side_effect = Exception("API Error")
        mock_calendar_list.list.return_value = mock_list
        mock_service.calendarList.return_value = mock_calendar_list
        
        mock_build.return_value = mock_service
        mock_auth.return_value = Mock()
        
        calendars = self.exporter.get_calendars()
        assert calendars == []
    
    def test_get_event_count(self):
        """Test getting event count."""
        with patch.object(self.exporter, 'export') as mock_export:
            mock_export.return_value = [self.sample_event, self.sample_all_day_event]
            
            count = self.exporter.get_event_count()
            
            assert count == 2
            mock_export.assert_called_once_with('primary', 7, 30)
    
    def test_get_event_count_error(self):
        """Test error handling in get_event_count."""
        with patch.object(self.exporter, 'export') as mock_export:
            mock_export.side_effect = Exception("Export error")
            
            count = self.exporter.get_event_count()
            assert count == 0
    
    def test_date_time_processing(self):
        """Test processing of different date/time formats."""
        events = [
            {
                'id': 'datetime_event',
                'summary': 'DateTime Event',
                'start': {'dateTime': '2023-01-15T10:00:00-08:00'},
                'end': {'dateTime': '2023-01-15T11:00:00-08:00'}
            },
            {
                'id': 'date_event',
                'summary': 'Date Event',
                'start': {'date': '2023-01-16'},
                'end': {'date': '2023-01-17'}
            }
        ]
        
        results = list(self.exporter.process(iter(events)))
        
        assert len(results) == 2
        
        # Check that both events have start/end times processed
        for doc in results:
            assert 'start' in doc.metadata
            assert 'end' in doc.metadata
            if 'start_ts' in doc.metadata:
                assert isinstance(doc.metadata['start_ts'], float)
            if 'end_ts' in doc.metadata:
                assert isinstance(doc.metadata['end_ts'], float)
    
    def test_attendees_processing(self):
        """Test processing of attendees with different formats."""
        event_with_attendees = {
            'id': 'attendees_event',
            'summary': 'Event with Attendees',
            'attendees': [
                {'displayName': 'Alice Johnson', 'email': 'alice@example.com'},
                {'email': 'bob@example.com'},  # No display name
                {'displayName': 'Charlie Brown'},  # No email
                {}  # Empty attendee
            ]
        }
        
        results = list(self.exporter.process(iter([event_with_attendees])))
        doc = results[0]
        
        attendees = doc.metadata['attendees']
        assert 'Alice Johnson' in attendees
        assert 'bob@example.com' in attendees
        assert 'Charlie Brown' in attendees
        # Empty attendee should be filtered out
        assert attendees.count(',') == 2  # 3 valid attendees = 2 commas
    
    def test_metadata_completeness(self):
        """Test that all expected metadata fields are present."""
        results = list(self.exporter.process(iter([self.sample_event])))
        doc = results[0]
        
        expected_fields = [
            'event_id', 'summary', 'description', 'location', 'organizer',
            'attendees', 'source', 'type', 'ingestion_timestamp', 'start',
            'end', 'start_ts', 'end_ts', 'recurringEventId', 'eventType',
            'status', 'visibility', 'creator'
        ]
        
        for field in expected_fields:
            assert field in doc.metadata, f"Missing metadata field: {field}"
    
    def test_content_structure(self):
        """Test the structure of generated document content."""
        results = list(self.exporter.process(iter([self.sample_event])))
        doc = results[0]
        
        content = doc.page_content
        
        # Check all sections are present
        assert 'Summary: Team Meeting' in content
        assert 'Description: Weekly team sync meeting' in content
        assert 'Location: Conference Room A' in content
        assert 'Organizer: John Doe' in content
        assert 'Attendees: Alice Johnson, bob@example.com' in content
        assert 'Start:' in content
        assert 'End:' in content