from datetime import datetime, timedelta
from typing import List, Optional
from prefect import flow, task
from prefect.blocks.system import Secret
from atlassian.bitbucket import Cloud
from langchain.schema import Document
from stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb

WORKSPACE_NAME = "omnidiandevelopmentteam"

def get_bitbucket_client() -> Cloud:
    secret_block = Secret.load("prefect-bitbucket-credentials")
    secret = secret_block.get()
    username = secret["username"]
    api_token = secret["app-password"]

    bb = Cloud(
        username=username,
        password=api_token
    )
    return bb

def iso_to_datetime(iso_str: str) -> datetime:
    # Ensures 'Z' replaced by '+00:00' for fromisoformat compatibility if needed
    if iso_str.endswith('Z'):
        iso_str = iso_str[:-1] + '+00:00'
    return datetime.fromisoformat(iso_str)
def format_pull_request_to_document(pr, workspace: str, project_key: str, repo_slug: str) -> Document:
    pr_data = pr.data
    # Construct a unique ID using workspace, project_key, repo_slug, and pr_id
    pr_id = f"{workspace}-{project_key}-{repo_slug}-{pr_data.get('id')}"
    pr_title = pr_data.get('title', '')
    pr_description = pr_data.get('description', '')

    author_info = pr_data.get('author', {})
    author_name = author_info.get('display_name', author_info.get('nickname', 'Unknown'))

    state = pr_data.get('state')
    created_on = pr_data.get('created_on')
    updated_on = pr_data.get('updated_on')

    participants = pr_data.get('participants', [])
    # Reviewers are participants who approved the PR
    reviewers_list = [p['user']['display_name'] for p in participants if p.get('approved', False)]
    # Join reviewers into a comma-separated string
    reviewers = ", ".join(reviewers_list) if reviewers_list else ""

    # Source and destination branches
    source_branch = pr_data.get('source', {}).get('branch', {}).get('name', 'Unknown')
    destination_branch = pr_data.get('destination', {}).get('branch', {}).get('name', 'Unknown')

    created_dt = iso_to_datetime(created_on) if created_on else None
    updated_dt = iso_to_datetime(updated_on) if updated_on else None

    # Fetch comments
    comments_text = ""
    comment_count = 0
    for comment in pr.comments():
        c_data = comment.data
        c_author = c_data.get('user', {}).get('display_name', 'Unknown')
        c_body = c_data.get('content', {}).get('raw', '')
        if comment_count == 0:
            comments_text += "\n########## Comments ##########\n"
        comments_text += f"{c_author}: {c_body}\n\n"
        comment_count += 1

    # Retrieve commit authors
    commit_authors_set = set()
    commit_text = []
    try:
        for c in pr.commits:
            c_data = c.data
            # Try user display_name first
            c_author_name = c_data.get('author', {}).get('user', {}).get('display_name')
            commit_text.append(f"{c_author_name}: {c.message}")
            if not c_author_name:
                # Fallback to raw author if display_name is not available
                c_author_name = c_data.get('author', {}).get('raw', 'Unknown')
            commit_authors_set.add(c_author_name)
    except:
        pass

    # Combine all participants: PR author, participants, and commit authors
    all_participants_set = set([author_name])  # include PR author
    all_participants_set.update([p['user']['display_name'] for p in participants if p.get('user')])
    all_participants_set.update(commit_authors_set)

    # Convert sets to comma-separated strings
    all_participants = ", ".join(sorted(all_participants_set))
    commit_authors = ", ".join(sorted(commit_authors_set))
    commit_text = "\n".join(commit_text)

    page_content = (
        f"{pr_title}\n{pr_description}\n{comments_text}"
    )

    metadata = {
        'id': pr_id,
        'workspace': workspace,
        'project_key': project_key,
        'repo_slug': repo_slug,
        'title': pr_title,
        'author_name': author_name,
        'state': state,
        'reviewers': reviewers,  # comma-separated string
        'source_branch': source_branch,
        'destination_branch': destination_branch,
        'all_participants': all_participants,  # comma-separated string
        'commit_authors': commit_authors,       # comma-separated string
    }

    if created_dt:
        metadata['created_ts'] = created_dt.timestamp()
        metadata['created'] = created_dt.isoformat()
    if updated_dt:
        metadata['updated_ts'] = updated_dt.timestamp()
        metadata['updated'] = updated_dt.isoformat()

    return Document(id=str(pr_id), page_content=page_content, metadata=metadata)

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
