from prefect import flow, task
from langchain.schema import Document
from typing import List
from prefect_data_getters.exporters import add_default_metadata
from prefect_data_getters.stores.document_types.jira_document import JiraDocument
from prefect_data_getters.stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb
#from prefect_data_getters.exporters.jira import get_jira_client, format_issue_to_document 
from prefect_data_getters.exporters import JiraExporter

jira_exporter = JiraExporter()
@task
def fetch_jira_issues(days_ago, projects) -> List[dict]:
    jira_exporter = JiraExporter()
    jira_docs = jira_exporter.export(days_ago=days_ago, projects=projects)
    return list(jira_docs)

@task
def process_issues_to_documents(issues: List[dict]) -> List[JiraDocument]:
    return list(jira_exporter.process(issues))

@task
def store_documents_in_vectorstore(documents: List[JiraDocument]):
    JiraDocument.save_documents(
        docs=documents,
        store_name="jira_issues",
        also_store_vectors=True
    )
    

@flow(name="jira-backup-flow", log_prints=True, timeout_seconds=3600)
def jira_backup_flow(days_ago: int = 180):
    # Step 1: Fetch issues from Jira
    issues = fetch_jira_issues(days_ago, projects=["HYP", "Ingest", "ONBRD", "client"])

    # Step 2: Process issues into documents
    documents = process_issues_to_documents(issues)

    # Log the number of processed issues
    print(f"Number of Jira issues processed: {len(documents)}")

    # Step 3: Store documents in vector store
    store_documents_in_vectorstore(documents)

if __name__ == '__main__':
    jira_backup_flow(2)