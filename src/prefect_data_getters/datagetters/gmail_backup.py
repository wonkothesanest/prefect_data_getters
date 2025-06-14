from prefect import flow, task
from langchain.schema import Document
from typing import List
import prefect
from prefect_data_getters.enrichers.gmail_email_processing_flow import process_emails_by_google_ids, utilize_analysis_flow
from prefect_data_getters.stores.document_types.email_document import EmailDocument
from prefect_data_getters.exporters.gmail_exporter import GmailExporter
from prefect.artifacts import create_markdown_artifact

@task
def fetch_gmail_messages(days_ago: int) -> List[dict]:
    """Fetch raw Gmail message data."""
    gmail_exporter = GmailExporter()
    gmail_docs = gmail_exporter.export(days_ago=days_ago)
    return list(gmail_docs)

@task
def process_messages_to_documents(raw_messages: List[dict]) -> List[Document]:
    """Process raw Gmail data into Document objects."""
    gmail_exporter = GmailExporter()
    documents = list(gmail_exporter.process(iter(raw_messages)))
    return documents

@task
def store_documents_in_vectorstore(documents: List[Document]):
    """Store Gmail documents in vector store."""
    if documents:
        EmailDocument.save_documents(
            docs=documents,
            store_name="email_messages",
            also_store_vectors=True
        )

@flow(name="gmail-mbox-backup-flow", log_prints=True, timeout_seconds=3600)
def gmail_mbox_backup_flow(days_ago: int = 1):
    # Step 1: Fetch raw Gmail messages
    raw_messages = fetch_gmail_messages(days_ago)
    create_markdown_artifact(f"Number of messages found: {len(raw_messages)} when pulling for {days_ago} days.")
    
    # Step 2: Process messages into Document objects
    documents = process_messages_to_documents(raw_messages)

    # Extract email IDs for return value (for backward compatibility)
    email_ids = [msg.get("google-id", msg.get("id", "")) for msg in raw_messages]

    if not raw_messages:
        print(f"No messages found from the past {days_ago} days.")
        return email_ids
    
    print(f"Retrieved {len(raw_messages)} messages. Processing...")
    
    # Step 3: Store documents in vector store
    store_documents_in_vectorstore(documents)
    return email_ids

@flow(name="Gmail Flow", log_prints=True, timeout_seconds=3600*3)
def gmail_flow(days_ago: int = 3):
    """
    Flow to retrieve and process Gmail messages.
    """
    logger = prefect.get_run_logger()
    # Get messages from the past given number of days
    email_ids = gmail_mbox_backup_flow(days_ago=days_ago)
    logger.info(f"Retrieved {len(email_ids)} messages. Processing...")
    processed_ids = process_emails_by_google_ids(email_ids, overwrite_existing=False)
    logger.info(f"Processed {len(processed_ids)} emails.")
    analyized_ids = utilize_analysis_flow(email_ids)
    logger.info(f"Analyzed {len(analyized_ids)} emails.")


# Example usage
if __name__ == "__main__":
    gmail_flow(days_ago=1)
