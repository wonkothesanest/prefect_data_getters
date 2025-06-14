from datetime import datetime, timedelta
from typing import List, Optional
from prefect import flow, task
from langchain.schema import Document
from prefect_data_getters.stores.document_types.bitbucket_document import BitbucketPR
from prefect_data_getters.exporters.bitbucket_exporter import BitbucketExporter

@task
def fetch_bitbucket_pull_requests(days_ago: int = 14) -> List[dict]:
    """Fetch raw Bitbucket pull request data."""
    bitbucket_exporter = BitbucketExporter()
    pr_docs = bitbucket_exporter.export(days_ago=days_ago)
    return list(pr_docs)

@task
def process_pull_requests_to_documents(raw_prs: List[dict]) -> List[Document]:
    """Process raw Bitbucket data into Document objects."""
    bitbucket_exporter = BitbucketExporter()
    documents = list(bitbucket_exporter.process(iter(raw_prs)))
    return documents

@task
def store_documents_in_vectorstore(documents: List[Document]):
    """Store Bitbucket pull request documents in vector store."""
    if documents:
        BitbucketPR.save_documents(
            docs=documents,
            store_name="bitbucket_pull_requests",
            also_store_vectors=True
        )

@flow(name="bitbucket-pr-backup-flow", log_prints=True, timeout_seconds=3600)
def bitbucket_pr_backup_flow(days_ago: int = 14):
    # Step 1: Fetch raw Bitbucket pull requests
    raw_pull_requests = fetch_bitbucket_pull_requests(days_ago)

    # Step 2: Process pull requests into Document objects
    documents = process_pull_requests_to_documents(raw_pull_requests)

    # Log the number of processed PRs
    print(f"Number of Bitbucket PRs processed: {len(documents)}")

    # Step 3: Store documents in vector store
    store_documents_in_vectorstore(documents)

if __name__ == '__main__':
    # Example usage:
    # bitbucket_pr_backup_flow(earliest_date="2023-01-01T00:00:00")
    bitbucket_pr_backup_flow(days_ago=3)
