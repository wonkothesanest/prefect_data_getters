import os
import shutil
from prefect import flow, task
from langchain.schema import Document
from typing import List

import prefect
from prefect_data_getters.enrichers.gmail_email_processing_flow import process_emails_by_google_ids, utilize_analysis_flow
from prefect_data_getters.exporters import add_default_metadata
from prefect_data_getters.exporters.gmail import process_message
from prefect_data_getters.stores.elasticsearch import upsert_documents
from prefect_data_getters.utilities import constants as C  
from prefect_data_getters.stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb
from langchain_community.vectorstores.utils import filter_complex_metadata
from prefect.artifacts import create_markdown_artifact

from prefect_data_getters.exporters.gmail import get_messages_by_query, parse_date
from prefect_data_getters.exporters.gmail import get_email_body

import os
from prefect import flow
from prefect_data_getters.exporters.gmail import get_messages, process_message
from elasticsearch import Elasticsearch

es_client = Elasticsearch(C.ES_URL)

@task
def retrieve_messages(days_ago: int):
    messages = get_messages(days_ago)
    return messages

@task 
def process_messages(messages: list):
    # Process each message
    documents = []
    for message in messages:
        try:
            documents.append(process_message(message))
        except Exception as e:
            print(f"Error processing message: {e}")
            continue
    return documents

@task
def store_documents_in_vectorstore(documents: List[Document]):
    embeddings, vectorstore = get_embeddings_and_vectordb("email_messages")
    batch_size = 1000  # Adjust based on your needs
    batch_process_and_store(documents, vectorstore)


@flow(name="gmail-mbox-backup-flow", log_prints=True)
def gmail_mbox_backup_flow(days_ago: int=1):
    # Get messages from the past given number of days
    messages = retrieve_messages(days_ago)
    create_markdown_artifact(f"Number of messages found: {len(messages)} when pulling for {days_ago} days.")
    # Store raw

    ret_emails = []
    for e in messages:
        try:
            d = {}
            d["text"] = get_email_body(e)

            for k in e.keys():
                d[k.lower()] = e[k]
            d["labels"] = d["labels"].split(",") if d["labels"] else []
            d["date"] = parse_date(d["date"])
            ret_emails.append(d)
        except Exception as e:
            print(f"Error processing message: {e}")
            continue

    upsert_documents(ret_emails, "email_messages_raw", "google-id")
    email_ids = [e["google-id"] for e in ret_emails]

    
    if not messages:
        print(f"No messages found from the past {days_ago} days.")
        return
    
    print(f"Retrieved {len(messages)} messages. Processing...")
    documents = process_messages(messages)
    i=1
    store_documents_in_vectorstore(documents)

    


@flow(name="Gmail Flow", log_prints=True, )
def gmail_flow(days_ago: int = 1):
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
    gmail_mbox_backup_flow(days_ago=10)
