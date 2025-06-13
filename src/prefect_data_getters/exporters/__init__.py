"""
Exporters module for data extraction from various sources.

This module provides both exporter classes and processing functions for document
transformation and enrichment. Exporters inherit from BaseExporter and provide
standardized interfaces for extracting data from different sources.
"""

from typing import Iterator
from langchain_core.documents import Document
from datetime import datetime
import logging

# Import with fallbacks for optional dependencies
try:
    from prefect_data_getters.stores.documents_new import AIDocument
    from prefect_data_getters.stores.document_registry import DocumentTypeRegistry
except ImportError:
    # Fallback if stores module is not available
    AIDocument = Document
    DocumentTypeRegistry = None

# Import exporters
from .base import BaseExporter

# Import exporters with fallbacks
try:
    from .gmail_exporter import GmailExporter
except ImportError:
    GmailExporter = None

try:
    from .slack_exporter import SlackExporter
except ImportError:
    SlackExporter = None

# Export the main classes
__all__ = [
    'BaseExporter',
    'GmailExporter',
    'SlackExporter',
    # Processing functions
    'add_ingestion_timestamp',
    'convert_to_ai_documents',
    'filter_by_metadata',
    'add_source_metadata',
    'batch_documents',
    'add_default_metadata'  # Legacy
]

logger = logging.getLogger(__name__)


def add_ingestion_timestamp(
    docs: Iterator[Document],
    metadata_field: str = "ingestion_timestamp"
) -> Iterator[Document]:
    """
    Add timestamp to document metadata with configurable field name.
    
    This function adds the current timestamp to each document's metadata,
    allowing tracking of when documents were processed. The timestamp
    is in ISO format for consistency.
    
    Args:
        docs: Iterator of documents to process
        metadata_field: Name of metadata field to store timestamp in
        
    Returns:
        Iterator[Document]: Iterator of documents with timestamp metadata added
        
    Yields:
        Document: Document with added timestamp metadata
        
    Example:
        >>> from langchain_core.documents import Document
        >>> docs = [Document(page_content="test", metadata={"source": "test"})]
        >>> processed = list(add_ingestion_timestamp(iter(docs)))
        >>> "ingestion_timestamp" in processed[0].metadata
        True
    """
    timestamp = datetime.now().isoformat()
    
    for doc in docs:
        try:
            # Ensure metadata exists
            if doc.metadata is None:
                doc.metadata = {}
            
            # Add timestamp to metadata
            doc.metadata[metadata_field] = timestamp
            
            yield doc
            
        except Exception as e:
            logger.error(f"Error adding timestamp to document: {e}")
            # Yield the document without timestamp rather than failing completely
            yield doc


def convert_to_ai_documents(
    docs: Iterator[Document],
    store_name: str
) -> Iterator[AIDocument]:
    """
    Convert Documents to AIDocuments using the registry.
    
    This function converts standard langchain Documents to AIDocument instances
    using the DocumentTypeRegistry to determine the appropriate document type
    based on the store name. This enables type-specific functionality and
    storage behavior.
    
    Args:
        docs: Iterator of Documents to convert
        store_name: Name of the store/index to determine document type
        
    Returns:
        Iterator[AIDocument]: Iterator of AIDocument instances
        
    Yields:
        AIDocument: Converted AIDocument instance
        
    Raises:
        ValueError: If store_name is not registered in DocumentTypeRegistry
        
    Example:
        >>> from langchain_core.documents import Document
        >>> docs = [Document(page_content="test", metadata={"source": "test"})]
        >>> ai_docs = list(convert_to_ai_documents(iter(docs), "email_messages"))
        >>> isinstance(ai_docs[0], AIDocument)
        True
    """
    for doc in docs:
        try:
            # Prepare data dictionary for document creation
            doc_data = {
                'page_content': doc.page_content,
                'metadata': doc.metadata or {},
            }
            
            # Add id if present
            if hasattr(doc, 'id') and doc.id:
                doc_data['id'] = doc.id
            
            # Create AIDocument using registry
            ai_doc = DocumentTypeRegistry.create_document(doc_data, store_name)
            
            # Preserve original id if it exists
            if hasattr(doc, 'id') and doc.id:
                ai_doc.id = doc.id
            
            yield ai_doc
            
        except Exception as e:
            logger.error(f"Error converting document to AIDocument: {e}")
            logger.error(f"Document content preview: {doc.page_content[:100]}...")
            # Continue processing other documents rather than failing completely
            continue


def filter_by_metadata(
    docs: Iterator[Document],
    metadata_key: str,
    metadata_value: str,
    exact_match: bool = True
) -> Iterator[Document]:
    """
    Filter documents based on metadata values.
    
    Args:
        docs: Iterator of documents to filter
        metadata_key: Metadata key to filter on
        metadata_value: Value to match against
        exact_match: If True, requires exact match; if False, checks if value is contained
        
    Returns:
        Iterator[Document]: Iterator of filtered documents
        
    Yields:
        Document: Documents that match the filter criteria
    """
    for doc in docs:
        try:
            if doc.metadata and metadata_key in doc.metadata:
                doc_value = str(doc.metadata[metadata_key])
                
                if exact_match:
                    if doc_value == metadata_value:
                        yield doc
                else:
                    if metadata_value.lower() in doc_value.lower():
                        yield doc
                        
        except Exception as e:
            logger.error(f"Error filtering document by metadata: {e}")
            # Continue processing other documents
            continue


def add_source_metadata(
    docs: Iterator[Document],
    source_name: str,
    source_type: str = None
) -> Iterator[Document]:
    """
    Add source information to document metadata.
    
    Args:
        docs: Iterator of documents to process
        source_name: Name of the data source (e.g., "gmail", "slack")
        source_type: Optional type of source (e.g., "email", "chat")
        
    Returns:
        Iterator[Document]: Iterator of documents with source metadata added
        
    Yields:
        Document: Document with added source metadata
    """
    for doc in docs:
        try:
            # Ensure metadata exists
            if doc.metadata is None:
                doc.metadata = {}
            
            # Add source information
            doc.metadata["source_name"] = source_name
            if source_type:
                doc.metadata["source_type"] = source_type
            
            yield doc
            
        except Exception as e:
            logger.error(f"Error adding source metadata to document: {e}")
            # Yield the document without source metadata rather than failing
            yield doc


def batch_documents(
    docs: Iterator[Document],
    batch_size: int = 100
) -> Iterator[list[Document]]:
    """
    Batch documents into groups for efficient processing.
    
    Args:
        docs: Iterator of documents to batch
        batch_size: Number of documents per batch
        
    Returns:
        Iterator[list[Document]]: Iterator of document batches
        
    Yields:
        list[Document]: Batch of documents
    """
    batch = []
    
    for doc in docs:
        batch.append(doc)
        
        if len(batch) >= batch_size:
            yield batch
            batch = []
    
    # Yield remaining documents if any
    if batch:
        yield batch


# Legacy function for backward compatibility
def add_default_metadata(docs: list[Document]) -> list[Document]:
    """
    Legacy function for backward compatibility.
    
    Args:
        docs: List of documents to process
        
    Returns:
        list[Document]: List of documents with default metadata added
        
    Note:
        This function is deprecated. Use add_ingestion_timestamp() instead.
    """
    import warnings
    warnings.warn(
        "add_default_metadata is deprecated. Use add_ingestion_timestamp() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Convert to iterator, process, and convert back to list
    processed_docs = add_ingestion_timestamp(iter(docs))
    return list(processed_docs)