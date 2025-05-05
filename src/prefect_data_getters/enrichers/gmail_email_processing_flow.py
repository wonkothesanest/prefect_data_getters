from datetime import datetime, timedelta
import logging
import prefect
from prefect import flow, task
from typing import List, Dict, Optional
from elasticsearch import Elasticsearch
from prefect_data_getters.exporters.gmail import get_messages_by_query, parse_date
from prefect_data_getters.exporters.gmail import get_email_body, apply_labels_to_email
import json
from prefect_data_getters.utilities import constants as C
from prefect_data_getters.enrichers.gmail_email_processor_take_3 import EmailExtractor
from prefect_data_getters.stores.elasticsearch import upsert_documents

es_client = Elasticsearch(C.ES_URL)
email_processor = EmailExtractor()

def check_existing_ids(email_ids: List[str]) -> List[str]:
    """Query Elasticsearch to find already-processed email IDs."""
    response = es_client.search(
        index="email_messages_llm_processed",
        query={"ids": {"values": email_ids}},
        size=len(email_ids),
    )
    existing_ids = [hit["_id"] for hit in response["hits"]["hits"]]
    return existing_ids


@task(retries=3)
def utilize_analysis(email_id: str, analysis: Dict):
    logger = prefect.get_run_logger()
    suggested_labels = analysis.get("categories", [])

    if(analysis.get("is_urgent", False)):
        suggested_labels.append("Urgent")
    if(analysis.get("is_important", False)):
        suggested_labels.append("Important")
    logger.debug(f"Suggested labels for email {email_id}: {suggested_labels}")
    apply_labels_to_email(email_id=email_id, 
                          category_labels=suggested_labels, 
                          team_labels=analysis.get("teams"), 
                          project_labels=analysis.get("projects"), 
                          sytems_labels=analysis.get("systems"))
        


@task(retries=3, refresh_cache=True)
def process_email_and_upsert(email: Dict) -> Dict:
    """Run summarization + extraction on a single email."""
    logger = prefect.get_run_logger()
    try:
        analysis = email_processor.parse_email(email)
        processed = {}
        processed["analysis"] = analysis
        processed["google-id"] = email["google-id"]
        processed["date"] = parse_date(email["date"])
        processed["date_processed"] = datetime.now().isoformat()
        processed["email_content"] = {"from": email.get("from"), "to": email.get("to"), "subject": email.get("subject"), "text": email.get("text"), "date": parse_date(email["date"])}
        upsert_documents([processed], "email_messages_llm_processed", "google-id")
        
        return processed
    except Exception as e:
        logger.error(f"Error processing email {email['google-id']}: {e}")
        raise e


@flow(name="Email Processing Flow", log_prints=True)
def process_emails_by_google_ids(google_ids: Optional[List[str]] | None = None, overwrite_existing: bool = False, num_search_if_no_ids: int = 300):
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
        try:
            process_email_and_upsert(email)
        except Exception as e:
            logger.error(f"Error processing email {email['google-id']}: {e}")
            continue
    return email_ids


@flow
def utilize_analysis_flow(email_ids: List[str]):
    """Utilize the analysis from the processed email."""
    logger = prefect.get_run_logger()
    # logger.setLevel(logging.DEBUG)
    for email_id in email_ids:
        try:
            retrieved_doc = es_client.get_source(index="email_messages_llm_processed", id=email_id)
            analysis = retrieved_doc.raw.get("analysis", {})
        except Exception as e:
            logger.error(f"Error retrieving email {email_id}: {e}")
            continue
        utilize_analysis(email_id, analysis)
        logger.debug(f"Utilized analysis for email {email_id}.")
    logger.info(f"Finished utilizing analysis for all emails in batch of len {len(email_ids)}.")
    return email_ids

if __name__ == "__main__":
    # <<< RUN THIS FUNCTION LOCALLY >>>
    process_emails_by_google_ids(None, overwrite_existing=True, num_search_if_no_ids=2)
    # utilize_analysis_flow(["1964ae6062ff64c5","1964a2ca44c1f35d", "1964960d3d237e64"])
    # response = es_client.search(index="email_messages_llm_processed", body={}, size=1000)
    # retrieved_docs = {doc["_id"]: doc["_source"] for doc in response["hits"]["hits"][475:]}
    # utilize_analysis_flow(list(retrieved_docs.keys()))
