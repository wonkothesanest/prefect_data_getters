"""
Gmail exporter module with backward compatibility.

This module maintains backward compatibility with the existing Gmail functionality
while using the new GmailExporter class internally.
"""

import warnings
from typing import List, Iterator
from langchain_core.documents import Document

# Create a default instance for backward compatibility
_default_exporter = None


def _get_default_exporter():
    """Get or create the default Gmail exporter instance."""
    global _default_exporter
    if _default_exporter is None:
        # Import here to avoid circular imports
        from prefect_data_getters.exporters.gmail_exporter import GmailExporter
        _default_exporter = GmailExporter()
    return _default_exporter


# Backward compatibility functions
def authenticate_gmail():
    """
    Authenticates with the Gmail API using OAuth.
    Credentials are stored in a pickle file for reuse.
    
    Note:
        This function is deprecated. Use GmailExporter class directly.
    """
    warnings.warn(
        "authenticate_gmail() is deprecated. Use GmailExporter class directly.",
        DeprecationWarning,
        stacklevel=2
    )
    exporter = _get_default_exporter()
    return exporter._authenticate()


def get_messages_by_query(query: str = "", maxResults=None):
    """
    Get messages by Gmail query.
    
    Args:
        query: Gmail search query
        maxResults: Maximum number of results
        
    Returns:
        List of email message objects
        
    Note:
        This function is deprecated. Use GmailExporter.export() method instead.
    """
    warnings.warn(
        "get_messages_by_query() is deprecated. Use GmailExporter.export() method instead.",
        DeprecationWarning,
        stacklevel=2
    )
    exporter = _get_default_exporter()
    service = exporter._get_gmail_service()
    label_mapping = exporter._get_label_mapping(service)
    return exporter._fetch_messages(service, query, maxResults)


def get_messages(days_ago):
    """
    Get all messages from the past given number of days.
    
    Args:
        days_ago: Number of days back to search
        
    Returns:
        List of email message objects
        
    Note:
        This function is deprecated. Use GmailExporter.export() method instead.
    """
    warnings.warn(
        "get_messages() is deprecated. Use GmailExporter.export() method instead.",
        DeprecationWarning,
        stacklevel=2
    )
    exporter = _get_default_exporter()
    query = exporter._build_default_query(days_ago)
    service = exporter._get_gmail_service()
    return exporter._fetch_messages(service, query)


def get_email_body(message) -> str:
    """
    Extracts the body from an email message.
    
    Args:
        message: Email message object
        
    Returns:
        Email body text
        
    Note:
        This function is deprecated. Use GmailExporter._extract_email_body() method instead.
    """
    warnings.warn(
        "get_email_body() is deprecated. Use GmailExporter._extract_email_body() method instead.",
        DeprecationWarning,
        stacklevel=2
    )
    exporter = _get_default_exporter()
    return exporter._extract_email_body(message)


def get_metadata(message):
    """
    Extract metadata from the Gmail message.
    
    Args:
        message: Email message object
        
    Returns:
        Dictionary of metadata
        
    Note:
        This function is deprecated. Use GmailExporter._extract_metadata() method instead.
    """
    warnings.warn(
        "get_metadata() is deprecated. Use GmailExporter._extract_metadata() method instead.",
        DeprecationWarning,
        stacklevel=2
    )
    exporter = _get_default_exporter()
    return exporter._extract_metadata(message)


def process_message(message) -> Document:
    """
    Process a Gmail message into a Document object.
    
    Args:
        message: Email message object
        
    Returns:
        Document object
        
    Note:
        This function is deprecated. Use GmailExporter.export() method instead.
    """
    warnings.warn(
        "process_message() is deprecated. Use GmailExporter.export() method instead.",
        DeprecationWarning,
        stacklevel=2
    )
    exporter = _get_default_exporter()
    service = exporter._get_gmail_service()
    label_mapping = exporter._get_label_mapping(service)
    return exporter._process_message(message, label_mapping)


def apply_labels_to_email(email_id: str, 
                         category_labels: List[str] = [], 
                         team_labels: List[str] = [],  
                         project_labels: List[str] = [],  
                         sytems_labels: List[str] = []):
    """
    Apply suggested labels to the processed email.
    
    Args:
        email_id: Gmail message ID
        category_labels: List of category labels
        team_labels: List of team labels
        project_labels: List of project labels
        sytems_labels: List of system labels (note: typo preserved for compatibility)
        
    Note:
        This function is deprecated. Use GmailExporter.apply_labels_to_email() method instead.
    """
    warnings.warn(
        "apply_labels_to_email() is deprecated. Use GmailExporter.apply_labels_to_email() method instead.",
        DeprecationWarning,
        stacklevel=2
    )
    exporter = _get_default_exporter()
    # Note: Fix the typo in parameter name
    exporter.apply_labels_to_email(
        email_id=email_id,
        category_labels=category_labels,
        team_labels=team_labels,
        project_labels=project_labels,
        systems_labels=sytems_labels  # Fix typo here
    )


def get_labels():
    """
    Get all Gmail labels.
    
    Returns:
        Dictionary mapping label IDs to names
        
    Note:
        This function is deprecated. Use GmailExporter.get_labels() method instead.
    """
    warnings.warn(
        "get_labels() is deprecated. Use GmailExporter.get_labels() method instead.",
        DeprecationWarning,
        stacklevel=2
    )
    exporter = _get_default_exporter()
    return exporter.get_labels()


def parse_date(date_string):
    """
    Parse date string from email headers.
    
    Args:
        date_string: Date string from email header
        
    Returns:
        Parsed datetime object or original string if parsing fails
        
    Note:
        This function is deprecated. Use utilities.parse_date() instead.
    """
    warnings.warn(
        "parse_date() is deprecated. Use utilities.parse_date() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    try:
        from prefect_data_getters.utilities import parse_date as util_parse_date
        return util_parse_date(date_string)
    except ImportError:
        # Fallback implementation
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_string)
        except (ValueError, TypeError):
            return date_string


# Import and re-export the main class
def __getattr__(name):
    """Dynamic import to avoid circular imports."""
    if name == 'GmailExporter':
        from prefect_data_getters.exporters.gmail_exporter import GmailExporter
        return GmailExporter
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Export the new class for direct use
__all__ = [
    'GmailExporter',
    # Backward compatibility functions
    'authenticate_gmail',
    'get_messages_by_query',
    'get_messages',
    'get_email_body',
    'get_metadata',
    'process_message',
    'apply_labels_to_email',
    'get_labels',
    'parse_date'
]
