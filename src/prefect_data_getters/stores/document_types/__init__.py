"""
Document types package.

This package contains all the specific document type implementations
that inherit from the base AIDocument class.
"""

# Import all document types to ensure they are registered
from prefect_data_getters.stores.document_types.jira_document import JiraDocument
from prefect_data_getters.stores.document_types.email_document import EmailDocument
from prefect_data_getters.stores.document_types.slack_document import SlackMessageDocument
from prefect_data_getters.stores.document_types.slab_document import SlabDocument, SlabChunkDocument
from prefect_data_getters.stores.document_types.bitbucket_document import BitbucketPR
from prefect_data_getters.stores.document_types.calendar_document import CalendarDocument

__all__ = [
    'JiraDocument',
    'EmailDocument',
    'SlackMessageDocument',
    'SlabDocument',
    'SlabChunkDocument',
    'BitbucketPR',
    'CalendarDocument'
]