# google_calendar_flow.py
from prefect import flow, task
from datetime import datetime, timedelta
from prefect_data_getters.exporters import add_default_metadata
from prefect_data_getters.stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb
from prefect_data_getters.exporters.google_calendar import authenticate_google_calendar, format_event_to_document
from langchain_community.vectorstores.utils import filter_complex_metadata

@task
def fetch_google_calendar_events(days: int) -> list:
    """
    Fetches Google Calendar events for the next and previous 'days' days starting from today (UTC).
    """
    from googleapiclient.discovery import build
    creds = authenticate_google_calendar()
    service = build("calendar", "v3", credentials=creds)
    
    now = datetime.utcnow()
    # Set the start of today (UTC)
    start_of_day = datetime(now.year, now.month, now.day) - timedelta(days=days)
    # Calculate the end date by adding the given number of days
    end_of_period = start_of_day + timedelta(days=days)
    
    # Format the dates in RFC3339 format with 'Z' (UTC) suffix
    timeMin = start_of_day.isoformat() + "Z"
    timeMax = end_of_period.isoformat() + "Z"
    events = []
    page_token = None
    while True:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=timeMin,
            timeMax=timeMax,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token
        ).execute()
        
        events.extend(events_result.get("items", []))
        page_token = events_result.get("nextPageToken")
        if not page_token:
            break
        
    print(f"Found {len(events)} events between {timeMin} and {timeMax}.")
    return events

@task
def process_calendar_events_to_documents(events: list) -> list:
    """
    Processes raw Google Calendar events into Document objects.
    """
    documents = []
    for event in events:
        doc = format_event_to_document(event)
        documents.append(doc)
    return add_default_metadata(documents)

@task
def store_documents_in_vectorstore(documents: list):
    """
    Stores the processed documents in the vector store.
    """
    embeddings, vectorstore = get_embeddings_and_vectordb("google_calendar_events")
    batch_process_and_store(documents, vectorstore)

@flow(name="google-calendar-backup-flow", log_prints=True)
def google_calendar_backup_flow(days: int = 1):
    """
    Main Prefect flow to:
      1. Fetch Google Calendar events for a given number of days.
      2. Process events into Documents.
      3. Store the Documents in the vector store.
    """
    events = fetch_google_calendar_events(days)
    documents = process_calendar_events_to_documents(events)
    documents = filter_complex_metadata(documents)

    print(f"Number of Google Calendar events processed: {len(documents)}")
    store_documents_in_vectorstore(documents)

if __name__ == '__main__':
    # Run the flow for 6 days of events; adjust the parameter as needed.
    google_calendar_backup_flow(days=3)
