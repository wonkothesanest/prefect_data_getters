"""
Desired fields that will be helpful for vector search

Base object:
key

Fields:
the following can be accessed where priority.name would look like issue["fields"]["priority"]["name"]
statuscategorychangedate
priority.name
status.name
status.statusCategory.name
creator.displayName
creator.accountId
subtasks
reporter.displayName
reporter.accountId
issuetype.name
issuetype.description
issuetype.subtask
issuetype.hierarchyLevel
project.name
project.key
resolutiondate
watches.watchCount
watches.isWatching
created
updated
description
summary
comment.comments[].author.displayName
comment.comments[].author.accountId
comment.comments[].body

"""

from prefect import flow, task
from prefect.blocks.system import Secret
from atlassian import Jira, Bitbucket
from atlassian.bitbucket import Cloud
from langchain.schema import Document
from typing import List
import utilities.constants as C  # Adjust the import based on your project structure
from stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb
from datetime import datetime

def get_jira_client() -> Jira:
    secret_block = Secret.load("jira-credentials")
    secret = secret_block.get()
    username = secret["username"]
    api_token = secret["api-token"]
    url = secret["url"]
    
    jira = Jira(
        url=url,
        username=username,
        password=api_token
    )

    return jira

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

def get_issue_value(issue: dict, field_path: str):
    """Extracts the value from the issue dict given a dot-separated field path."""
    fields = field_path.split('.')
    value = issue
    for field in fields:
        if isinstance(value, dict):
            value = value.get(field, None)
        elif isinstance(value, list) and field.isdigit():
            index = int(field)
            if index < len(value):
                value = value[index]
            else:
                value = None
        else:
            value = None
        if value is None:
            break
    return value

DESIRED_FIELDS = [
    'statuscategorychangedate',
    'priority.name',
    'status.name',
    'status.statusCategory.name',
    'creator.displayName',
    'reporter.displayName',
    'assignee.displayName',
    'issuetype.name',
    'issuetype.description',
    'issuetype.subtask',
    'issuetype.hierarchyLevel',
    'project.name',
    'project.key',
    'resolutiondate',
    'watches.watchCount',
    'watches.isWatching',
    'priority.name',
    'created',
    'updated',
    # Comments
    'comment.comments',
]

def format_issue_to_document(issue: dict) -> Document:
    # Use issue key as the document ID
    doc_id = issue.get('key', '')

    # Extract summary and description for the content
    summary = get_issue_value(issue, 'fields.summary') or ''
    description = get_issue_value(issue, 'fields.description') or ''
    content = f"{summary}\n\n{description}\n\n"

    # Flatten metadata
    metadata = {'key': doc_id}
    for field in DESIRED_FIELDS:
        if field == 'comment.comments':
            # Handle comments
            comments = get_issue_value(issue, 'fields.comment.comments') or []
            comments_list = []
            first_comment = True
            for comment in comments:
                author_name = get_issue_value(comment, 'author.displayName')
                body = get_issue_value(comment, 'body')
                comment_text = f"{author_name}: {body}"
                comments_list.append(comment_text)
                if(first_comment):
                    content += "########## Comments ##########"
                    first_comment = False
                content += comment_text + "\n\n"
        elif field == "created" or field == "updated":
            value = get_issue_value(issue, f'fields.{field}')
            try:
                tsValue = datetime.fromisoformat(value).timestamp()
                metadata[f"{field.replace('.', '_')}_ts"] = tsValue
                metadata[field.replace('.', '_')] = value
            except:
                pass
        else:
            value = get_issue_value(issue, f'fields.{field}')
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            elif isinstance(value, dict):
                value = str(value)
            metadata[field.replace('.', '_')] = value

    # Ensure metadata is flat and serializable
    metadata = {k: v for k, v in metadata.items() if v is not None}
    if(len(metadata) == 0):
        metadata = {}
    document = Document(id=doc_id, page_content=content, metadata=metadata)

    return document


def _iso_to_datetime(iso_str: str) -> datetime:
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

    created_dt = _iso_to_datetime(created_on) if created_on else None
    updated_dt = _iso_to_datetime(updated_on) if updated_on else None

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