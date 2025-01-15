from datetime import datetime, timedelta
from typing import List, Optional
from prefect import flow, task
from prefect.blocks.system import Secret
from atlassian.bitbucket import Cloud
from langchain.schema import Document
from prefect_data_getters.exporters.jira import get_bitbucket_client, format_pull_request_to_document
from prefect_data_getters.stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb

WORKSPACE_NAME = "omnidiandevelopmentteam"

def fetch_all_recent_pull_requests(earliest_date: Optional[datetime] = (datetime.now() - timedelta(weeks=2)).isoformat()) -> List[Document]:
    bb = get_bitbucket_client()
    w = bb.workspaces.get(WORKSPACE_NAME)

    all_documents = []

    # Construct query if earliest_date is provided
    q = None
    if earliest_date:
        iso_date = earliest_date.isoformat()
        # If missing timezone info, add 'Z'
        if 'Z' not in iso_date and '+' not in iso_date:
            iso_date += 'Z'
        q = f'updated_on >= "{iso_date}"'

    # Iterate over all projects
    for project in w.projects.each():
        project_data = project.data
        project_key = project_data.get('key')

        # Iterate over all repositories in the project
        for repo in project.repositories.each():
            repo_data = repo.data
            repo_slug = repo_data.get('slug')

            # Iterate over PRs, optionally filtered by q
            # Set state='ALL' to get all PRs regardless of state
            # Pagination is handled by `each()`
            for pr in repo.pullrequests.each(q=q):
                # pr is an object, pr.data is the dict
                # If earliest_date not provided, we just take them all
                # If earliest_date provided, `q` query ensures we only get updated_on >= earliest_date
                doc = format_pull_request_to_document(pr, WORKSPACE_NAME, project_key, repo_slug)
                all_documents.append(doc)

    return all_documents

@task
def fetch_all_recent_pull_requests_task(earliest_date: Optional[datetime] = None) -> List[Document]:
    return fetch_all_recent_pull_requests(earliest_date)

@task
def store_documents_in_vectorstore(documents: List[Document]):
    embeddings, vectorstore = get_embeddings_and_vectordb("bitbucket_pull_requests")
    batch_process_and_store(documents, vectorstore, batch_size=1000)

@flow(name="bitbucket-pr-backup-flow", log_prints=True)
def bitbucket_pr_backup_flow(earliest_date: Optional[str] = None):
    # If earliest_date is provided as a string, parse it into a datetime
    dt = None
    if earliest_date:
        dt = datetime.fromisoformat(earliest_date)

    # Step 1: Fetch all recent PRs (or all if earliest_date not given)
    documents = fetch_all_recent_pull_requests_task(dt)

    # Log the number of processed PRs
    print(f"Number of PRs processed: {len(documents)}")

    # Step 2: Store documents in vector store
    store_documents_in_vectorstore(documents)

if __name__ == '__main__':
    # Example usage:
    # bitbucket_pr_backup_flow(earliest_date="2023-01-01T00:00:00")
    bitbucket_pr_backup_flow(earliest_date=(datetime.now() - timedelta(weeks=2)).isoformat())
