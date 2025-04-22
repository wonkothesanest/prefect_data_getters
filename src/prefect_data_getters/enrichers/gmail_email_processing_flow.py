from datetime import timedelta
import prefect
from prefect import flow, task
from typing import List, Dict
from elasticsearch import Elasticsearch
from prefect_data_getters.exporters.gmail import get_messages_by_query, parse_date
from prefect_data_getters.exporters.gmail import get_email_body
import json
from prefect_data_getters.utilities import constants as C
from prefect_data_getters.enrichers.gmail_email_processor import EmailProcessor
from prefect_data_getters.stores.elasticsearch import upsert_documents

es_client = Elasticsearch(C.ES_URL)
email_processor = EmailProcessor()



def check_existing_ids( email_ids: List[str]) -> List[str]:
    """Query Elasticsearch to find already-processed email IDs."""
    response = es_client.search(
        index="email_messages_llm_processed",
        query={"ids": {"values": email_ids}}
    )
    existing_ids = [hit["_id"] for hit in response["hits"]["hits"]]
    return existing_ids

@task
def upload_to_elasticsearch( processed_email: Dict):
    """Upsert processed email into Elasticsearch."""
    if(processed_email is None):
        return
    es_client.update(
        index="email_messages_llm_processed",
        id=processed_email["google-id"],
        body={
            "doc": processed_email,
            "doc_as_upsert": True
        }
    )
    
@task(retries=3, refresh_cache=True )
def process_email_and_upsert( email: Dict) -> Dict:
    """Run summarization + extraction on a single email."""
    logger = prefect.get_run_logger()
    try:
        processed = email_processor.process_email(email)
        
        processed["google-id"]= email["google-id"]
        processed["email_content"] = {"subject": email["subject"], "text": email["text"]}
        upsert_documents([processed], "email_messages_llm_processed", "google-id")
        return processed
    except Exception as e:
        logger.error(f"Error processing email {email['google-id']}: {e}")
        return None
    

@flow(name="Email Processing Flow", log_prints=True)
def process_emails_by_google_ids(google_ids: List[str] | None  = None, overwrite_existing: bool = False, num_search_if_no_ids: int = 300):
    logger = prefect.get_run_logger()

    if not google_ids:
        # Retrieve the top `num_docs` documents ordered by date in descending order
        query = {"sort": [{"date": {"order": "desc"}}]}
        response = es_client.search(index="email_messages_raw", body=query, size=num_search_if_no_ids)
        retrieved_docs = {doc["_id"]: doc["_source"] for doc in response["hits"]["hits"]}
        logger.info(f"Retrieved top {len(retrieved_docs)} documents ordered by date.")
    else:
        # Retrieve messages based on provided Google IDs
        query = {"query": {"ids": {"values": google_ids}}}
        response = es_client.search(index="email_messages_raw", body=query, size=len(google_ids))
        retrieved_docs = {doc["_id"]: doc["_source"] for doc in response["hits"]["hits"]}

        # Log missing IDs
        missing_ids = [google_id for google_id in google_ids if google_id not in retrieved_docs]
        if missing_ids:
            logger.warning(f"Missing Google IDs: {missing_ids}")

    email_ids = list(retrieved_docs.keys())

    if not overwrite_existing:
        existing_ids = check_existing_ids(email_ids)
        logger.info(f"Found {len(existing_ids)} already processed emails.")
        new_emails = [email for email in retrieved_docs.values() if email["google-id"] not in existing_ids]
    else:
        new_emails = list(retrieved_docs.values())

    logger.info(f"Processing {len(new_emails)} new emails.")
    for email in new_emails:
        processed = process_email_and_upsert(email)
        upload_to_elasticsearch(processed)



    


if __name__ == "__main__":
    # <<< RUN THIS FUNCTION LOCALLY >>>
    process_emails_by_google_ids(None)