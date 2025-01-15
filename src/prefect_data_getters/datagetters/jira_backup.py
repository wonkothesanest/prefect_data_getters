from prefect import flow, task
from prefect.blocks.system import Secret
from atlassian import Jira
from langchain.schema import Document
from typing import List
from prefect_data_getters.exporters import add_default_metadata
import prefect_data_getters.utilities.constants as C  
from prefect_data_getters.stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb, ESVectorStore
from datetime import datetime
from prefect_data_getters.exporters.jira import get_jira_client, format_issue_to_document 

@task
def fetch_jira_issues(jql: str, max_results: int = 100) -> List[dict]:
    jira = get_jira_client()
    all_issues = []
    start_at = 0
    total = 1  # Initialize to enter the loop
    while start_at < total:
        response = jira.jql(jql, start=start_at, limit=max_results)
        issues = response.get('issues', [])
        total = response.get('total', 0)
        all_issues.extend(issues)
        start_at += max_results
        print(f"Finished with batch at {start_at} of {total}...")
    return all_issues

@task
def process_issues_to_documents(issues: List[dict]) -> List[Document]:
    documents = []
    for issue in issues:
        doc = format_issue_to_document(issue)
        documents.append(doc)
    return add_default_metadata(documents)

@task
def store_documents_in_vectorstore(documents: List[Document]):
    embeddings, vectorstore = get_embeddings_and_vectordb("jira_issues")
    batch_size = 1000  # Adjust based on your needs
    batch_process_and_store(documents, vectorstore)

@flow(name="jira-backup-flow", log_prints=True)
def jira_backup_flow():
    # Define the JQL query
    jql_query = 'updated >= -180d AND (project = HYP OR project = Ingest OR project = ONBRD OR project = client)'

    # Step 1: Fetch issues from Jira
    issues = fetch_jira_issues(jql_query)

    # Step 2: Process issues into documents
    documents = process_issues_to_documents(issues)

    # Log the number of processed issues
    print(f"Number of Jira issues processed: {len(documents)}")

    # Step 3: Store documents in vector store
    store_documents_in_vectorstore(documents)

if __name__ == '__main__':
    jira_backup_flow()