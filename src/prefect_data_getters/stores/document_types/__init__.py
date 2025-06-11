"""
Document types package.

This package contains all the specific document type implementations
that inherit from the base AIDocument class.
"""

# Import all document types to ensure they are registered
from .jira_document import JiraDocument
from .email_document import EmailDocument
from .slack_document import SlackMessageDocument
from .slab_document import SlabDocument, SlabChunkDocument
from .bitbucket_document import BitbucketPR

__all__ = [
    'JiraDocument',
    'EmailDocument', 
    'SlackMessageDocument',
    'SlabDocument',
    'SlabChunkDocument',
    'BitbucketPR'
]