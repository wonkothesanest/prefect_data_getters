# google_calendar_flow.py
from prefect import flow, task
from datetime import datetime, timedelta
from langchain.schema import Document
from typing import List
from prefect_data_getters.exporters.calendar_exporter import CalendarExporter
from prefect_data_getters.stores.document_types.email_document import EmailDocument  # Using EmailDocument as fallback since no CalendarDocument exists

@task
def fetch_google_calendar_events(days_ago: int = 7, days_ahead: int = 30) -> List[dict]:
    """Fetch raw Google Calendar event data."""
    calendar_exporter = CalendarExporter()
    calendar_docs = calendar_exporter.export(days_ago=days_ago, days_ahead=days_ahead)
    return list(calendar_docs)

@task
def process_events_to_documents(raw_events: List[dict]) -> List[Document]:
    """Process raw Google Calendar data into Document objects."""
    calendar_exporter = CalendarExporter()
    documents = list(calendar_exporter.process(iter(raw_events)))
    return documents

@task
def store_documents_in_vectorstore(documents: List[Document]):
    """Store Google Calendar documents in vector store."""
    if documents:
        # Note: Using EmailDocument as fallback since no specific CalendarDocument exists
        # This could be improved by creating a dedicated CalendarDocument class
        EmailDocument.save_documents(
            docs=documents,
            store_name="google_calendar_events",
            also_store_vectors=True
        )

@flow(name="google-calendar-backup-flow", log_prints=True, timeout_seconds=3600)
def google_calendar_backup_flow(days_ago: int = 7, days_ahead: int = 30):
    """
    Main Prefect flow to:
      1. Fetch Google Calendar events for a given date range.
      2. Process events into Documents.
      3. Store the Documents in the vector store.
    """
    # Step 1: Fetch raw Google Calendar events
    raw_events = fetch_google_calendar_events(days_ago, days_ahead)
    
    # Step 2: Process events into Document objects
    documents = process_events_to_documents(raw_events)

    print(f"Number of Google Calendar events processed: {len(documents)}")
    
    # Step 3: Store documents in vector store
    store_documents_in_vectorstore(documents)

if __name__ == '__main__':
    # Run the flow for 6 days of events; adjust the parameter as needed.
    google_calendar_backup_flow(days=3)
