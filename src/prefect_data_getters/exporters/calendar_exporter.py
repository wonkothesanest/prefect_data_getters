"""
Google Calendar exporter implementation using the BaseExporter architecture.

This module provides the CalendarExporter class that inherits from BaseExporter,
implementing Google Calendar-specific functionality for exporting calendar events.
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import Iterator, Optional, Dict, Any, List

from langchain_core.documents import Document
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_fixed

from prefect_data_getters.exporters.base import BaseExporter
from prefect_data_getters.exporters.jira import _iso_to_datetime


class CalendarExporter(BaseExporter):
    """
    Google Calendar exporter that inherits from BaseExporter.
    
    This class provides functionality to export Google Calendar events as Document objects,
    with support for authentication, date range filtering, and event processing.
    
    Attributes:
        SCOPES: Google Calendar API scopes required for access
        _service: Cached Google Calendar service instance
        _credentials: Cached Google API credentials
    """
    
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Calendar exporter.
        
        Args:
            config: Configuration dictionary containing:
                - token_path: Path to Google token pickle file (default: "secrets/google_token.pickle")
                - credentials_path: Path to Google credentials JSON (default: "secrets/google_app_creds.json")
                - max_retries: Maximum number of API retry attempts (default: 3)
                - retry_delay: Delay between retries in seconds (default: 2)
        """
        super().__init__(config)
        self._service = None
        self._credentials = None
        
        # Configuration paths
        self._token_path = self._get_config("token_path", "secrets/google_token.pickle")
        self._credentials_path = self._get_config("credentials_path", "secrets/google_app_creds.json")
    
    def export(self, 
               calendar_id: str = "primary", 
               days_ago: int = 7,
               days_ahead: int = 30,
               max_results: int = None) -> Iterator[Dict[str, Any]]:
        """
        Export raw Google Calendar event data.
        
        Args:
            calendar_id: Calendar ID to export from (default: "primary")
            days_ago: Number of days in the past to include (default: 7)
            days_ahead: Number of days in the future to include (default: 30)
            max_results: Maximum number of events to return (optional)
            
        Returns:
            Iterator of dictionaries containing raw Google Calendar event data
            
        Yields:
            Dict containing raw event data from Google Calendar API
        """
        service = self._get_calendar_service()
        
        # Calculate date range
        now = datetime.utcnow()
        start_date = now - timedelta(days=days_ago)
        end_date = now + timedelta(days=days_ahead)
        
        # Format dates in RFC3339 format with 'Z' (UTC) suffix
        time_min = start_date.isoformat() + "Z"
        time_max = end_date.isoformat() + "Z"
        
        self._log_info(f"Exporting calendar events from {calendar_id}")
        self._log_info(f"Date range: {time_min} to {time_max}")
        
        events_count = 0
        page_token = None
        
        while True:
            try:
                # Build request parameters
                request_params = {
                    'calendarId': calendar_id,
                    'timeMin': time_min,
                    'timeMax': time_max,
                    'singleEvents': True,
                    'orderBy': 'startTime',
                    'pageToken': page_token
                }
                
                if max_results:
                    request_params['maxResults'] = max_results
                
                # Execute API request
                events_result = service.events().list(**request_params).execute()
                events = events_result.get('items', [])
                
                for event in events:
                    yield event
                    events_count += 1
                
                # Check for next page
                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break
                    
                # Respect max_results if specified
                if max_results and events_count >= max_results:
                    break
                    
            except Exception as e:
                self._log_error(f"Error fetching calendar events: {e}")
                break
        
        self._log_info(f"Exported {events_count} calendar events")
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """
        Process raw Google Calendar data into Document objects.
        
        Args:
            raw_data: Iterator of raw Google Calendar event data from export()
            
        Returns:
            Iterator of Document objects with processed Calendar metadata
            
        Yields:
            Document objects with Google Calendar event-specific metadata and content
        """
        for event in raw_data:
            try:
                # Extract event information
                event_id = event.get("id", "")
                summary = event.get("summary", "")
                description = event.get("description", "")
                location = event.get("location", "")
                
                # Process start and end times
                start_info = event.get("start", {})
                end_info = event.get("end", {})
                
                # Use dateTime if available, else fallback to date
                start_time = start_info.get("dateTime", start_info.get("date", ""))
                end_time = end_info.get("dateTime", end_info.get("date", ""))
                
                # Convert to datetime objects and ISO format
                start_dt = None
                end_dt = None
                if start_time:
                    start_dt = _iso_to_datetime(start_time)
                    start_time = start_dt.isoformat()
                if end_time:
                    end_dt = _iso_to_datetime(end_time)
                    end_time = end_dt.isoformat()
                
                # Process organizer
                organizer_info = event.get("organizer", {})
                organizer = organizer_info.get("displayName", organizer_info.get("email", ""))
                
                # Process attendees
                attendees_list = event.get("attendees", [])
                attendees = ", ".join([
                    attendee.get("displayName", attendee.get("email", ""))
                    for attendee in attendees_list
                    if attendee.get("displayName") or attendee.get("email")
                ])
                
                # Build content
                content_parts = []
                if summary:
                    content_parts.append(f"Summary: {summary}")
                if description:
                    content_parts.append(f"Description: {description}")
                if start_time:
                    content_parts.append(f"Start: {start_time}")
                if end_time:
                    content_parts.append(f"End: {end_time}")
                if location:
                    content_parts.append(f"Location: {location}")
                if organizer:
                    content_parts.append(f"Organizer: {organizer}")
                if attendees:
                    content_parts.append(f"Attendees: {attendees}")
                
                page_content = "\n".join(content_parts)
                
                # Build metadata
                metadata = {
                    "event_id": event_id,
                    "summary": summary,
                    "description": description,
                    "location": location,
                    "organizer": organizer,
                    "attendees": attendees,
                    "source": "google_calendar",
                    "type": "calendar_event",
                    "ingestion_timestamp": datetime.now().isoformat()
                }
                
                # Add time information
                if start_time:
                    metadata["start"] = start_time
                if end_time:
                    metadata["end"] = end_time
                if start_dt:
                    metadata["start_ts"] = start_dt.timestamp()
                if end_dt:
                    metadata["end_ts"] = end_dt.timestamp()
                
                # Add optional fields
                if event.get("recurringEventId"):
                    metadata["recurringEventId"] = event["recurringEventId"]
                if event.get("eventType"):
                    metadata["eventType"] = event["eventType"]
                if event.get("status"):
                    metadata["status"] = event["status"]
                if event.get("visibility"):
                    metadata["visibility"] = event["visibility"]
                
                # Add creator information
                creator_info = event.get("creator", {})
                if creator_info:
                    metadata["creator"] = creator_info.get("displayName", creator_info.get("email", ""))
                
                yield Document(
                    id=event_id,
                    page_content=page_content,
                    metadata=metadata
                )
                
            except Exception as e:
                self._log_error(f"Error processing calendar event: {e}")
                continue
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_calendar_service(self):
        """
        Get authenticated Google Calendar service with retry logic.
        
        Returns:
            Authenticated Google Calendar service instance
        """
        if self._service is None:
            try:
                credentials = self._authenticate_google_calendar()
                self._service = build("calendar", "v3", credentials=credentials)
                self._log_info("Successfully authenticated with Google Calendar API")
            except Exception as e:
                self._log_error(f"Failed to authenticate with Google Calendar: {e}")
                raise
        
        return self._service
    
    def _authenticate_google_calendar(self):
        """
        Authenticate with the Google Calendar API using OAuth.
        Credentials are stored in a pickle file for reuse.
        
        Returns:
            Authenticated credentials object
        """
        creds = None
        
        # Load saved credentials if they exist
        if os.path.exists(self._token_path):
            try:
                with open(self._token_path, "rb") as token:
                    creds = pickle.load(token)
                self._log_info(f"Loaded existing credentials from {self._token_path}")
            except Exception as e:
                self._log_warning(f"Error loading existing credentials: {e}")
        
        # If there are no valid credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self._log_info("Refreshed expired credentials")
                except Exception as e:
                    self._log_warning(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self._credentials_path):
                    raise FileNotFoundError(f"Google credentials file not found: {self._credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path, 
                    self.SCOPES
                )
                creds = flow.run_local_server(port=8080, access_type='offline')
                self._log_info("Obtained new credentials via OAuth flow")
            
            # Save the credentials for the next run
            try:
                os.makedirs(os.path.dirname(self._token_path), exist_ok=True)
                with open(self._token_path, "wb") as token:
                    pickle.dump(creds, token)
                self._log_info(f"Saved credentials to {self._token_path}")
            except Exception as e:
                self._log_warning(f"Error saving credentials: {e}")
        
        return creds
    
    def get_calendars(self) -> List[Dict[str, str]]:
        """
        Get list of available calendars.
        
        Returns:
            List of dictionaries with calendar information
        """
        service = self._get_calendar_service()
        
        try:
            calendars_result = service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            calendar_list = []
            for calendar in calendars:
                calendar_list.append({
                    'id': calendar.get('id'),
                    'summary': calendar.get('summary'),
                    'description': calendar.get('description', ''),
                    'primary': calendar.get('primary', False),
                    'accessRole': calendar.get('accessRole', '')
                })
            
            return calendar_list
            
        except Exception as e:
            self._log_error(f"Error fetching calendar list: {e}")
            return []
    
    def get_event_count(self, 
                       calendar_id: str = "primary", 
                       days_ago: int = 7,
                       days_ahead: int = 30) -> int:
        """
        Get count of events in the specified date range.
        
        Args:
            calendar_id: Calendar ID to count events from
            days_ago: Number of days in the past to include
            days_ahead: Number of days in the future to include
            
        Returns:
            Number of events in the date range
        """
        try:
            events = list(self.export(calendar_id, days_ago, days_ahead))
            return len(events)
        except Exception as e:
            self._log_error(f"Error counting events: {e}")
            return 0