# google_calendar_processor.py
from datetime import datetime
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from langchain.schema import Document

from prefect_data_getters.exporters.jira import _iso_to_datetime

# Define the scope for read-only calendar access
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def authenticate_google_calendar():
    """
    Authenticates with the Google Calendar API using OAuth.
    Credentials are stored in a pickle file for reuse.
    """
    creds = None
    token_path = "secrets/google_token.pickle"
    creds_path = "secrets/google_app_creds.json"
    
    # Load saved credentials if they exist
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)
    
    # If there are no valid credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=8080, access_type='offline')
        # Save the credentials for the next run
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
    
    return creds

def format_event_to_document(event: dict) -> Document:
    """
    Converts a Google Calendar event dictionary into a langchain Document.
    Extracts key fields and builds a content string plus metadata.
    """
    event_id = event.get("id", "")
    summary = event.get("summary", "")
    description = event.get("description", "")
    
    start_info = event.get("start", {})
    end_info = event.get("end", {})
    # Use dateTime if available, else fallback to date
    start_time = start_info.get("dateTime", start_info.get("date", ""))
    start_time = _iso_to_datetime(start_time).isoformat()
    end_time = end_info.get("dateTime", end_info.get("date", ""))
    end_time = _iso_to_datetime(end_time).isoformat()
    
    location = event.get("location", "")
    # Try to use displayName; if not available, fallback to email.
    organizer = event.get("organizer", {}).get("displayName", event.get("organizer", {}).get("email", ""))
    
    attendees_list = event.get("attendees", [])
    attendees = ", ".join(
        [
            attendee.get("displayName", attendee.get("email", ""))
            for attendee in attendees_list
        ]
    )
    
    content = (
        f"Summary: {summary}\n"
        f"Description: {description}\n"
        f"Start: {start_time}\n"
        f"End: {end_time}\n"
        f"Location: {location}\n"
        f"Organizer: {organizer}\n"
        f"Attendees: {attendees}"
    )
    
    metadata = {
        "event_id": event_id,
        "summary": summary,
        "description": description,
        "start": start_time,
        "end": end_time,
        "recurringEventId": event.get("recurringEventId"),
        "location": location,
        "organizer": organizer,
        "attendees": attendees,
        "eventType": event.get("eventType")

    }
    
    return Document(id=event_id, page_content=content, metadata=metadata)
