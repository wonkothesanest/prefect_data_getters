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

def get_bitbucket_client() -> Jira:
    secret_block = Secret.load("prefect-bitbucket-credentials")
    secret = secret_block.get()
    username = secret["username"]
    api_token = secret["api-token"]
    url = secret["url"]
    
    bb = Bitbucket(
        url=url,
        username=username,
        password=api_token
    )
    bb.get_pull_request()
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