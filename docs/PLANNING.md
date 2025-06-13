# Prefect Data Getters - Loosely Coupled Exporter Architecture

## Project Overview

This project is a data ingestion and RAG (Retrieval Augmented Generation) system that extracts data from multiple sources (Gmail, Slack, Jira, Slab, Bitbucket, Google Calendar), processes it, and stores it in both Elasticsearch (for text search) and vector stores (for semantic search).

## Current Architecture Status

The project is transitioning from a tightly coupled architecture to a loosely coupled, functional approach that emphasizes:
- Independent, composable exporters
- Functional processing pipelines
- Separation of concerns between extraction, processing, and storage

## Core Architectural Principles

### 1. Loose Coupling
- Exporters are independent and don't know about processing or storage
- Processing functions are composable and don't know about specific data sources
- Storage is completely separate from extraction and processing

### 2. Abstract Base Classes with Concrete Signatures
- All exporters inherit from `BaseExporter` abstract class
- Each exporter has specific method signatures for IDE code completion
- Common functionality is shared through inheritance

### 3. Functional Processing
- Processing steps are simple functions that can be composed
- Each function takes an iterator and returns an iterator
- Functions are reusable across different data sources

### 4. Type Safety
- Use type hints throughout
- Pydantic for data validation where appropriate
- Clear interfaces between components

## Directory Structure

```
src/prefect_data_getters/
├── exporters/
│   ├── __init__.py          # Common processing functions and utilities
│   ├── base.py              # BaseExporter abstract class
│   ├── gmail.py             # GmailExporter(BaseExporter)
│   ├── slack.py             # SlackExporter(BaseExporter)
│   ├── jira.py              # JiraExporter(BaseExporter)
│   ├── slab.py              # SlabExporter(BaseExporter)
│   ├── bitbucket.py         # BitbucketExporter(BaseExporter)
│   └── calendar.py          # CalendarExporter(BaseExporter)
├── datagetters/             # Existing Prefect workflows (do not modify)
│   ├── gmail_backup.py      # Existing Gmail Prefect flows
│   ├── slack_flow.py        # Existing Slack Prefect flows
│   └── ...                  # Other existing flows
└── stores/                  # Existing document and storage system (do not modify)
    ├── documents_new.py     # AIDocument classes
    ├── document_registry.py # Document type registry
    ├── elasticsearch_manager.py
    └── vectorstore.py
```

## Key Components

### BaseExporter Abstract Class (Enhanced Pattern)
```python
from abc import ABC, abstractmethod
from typing import Iterator, Any, Dict
from langchain_core.documents import Document

class BaseExporter(ABC):
    """Abstract base class for all data exporters with separated export and process methods."""
    
    @abstractmethod
    def export(self, **kwargs) -> Iterator[Any]:
        """Export raw data from the data source."""
        pass
    
    @abstractmethod
    def process(self, raw_data: Iterator[Any]) -> Iterator[Document]:
        """Process raw data into Document objects."""
        pass
    
    def export_documents(self, **kwargs) -> Iterator[Document]:
        """Convenience method that combines export and process for backward compatibility."""
        raw_data = self.export(**kwargs)
        return self.process(raw_data)
```

### Concrete Exporters with Specific Signatures (Updated Pattern)
```python
class GmailExporter(BaseExporter):
    def export(self, days_ago: int = 7, query: str = None, max_results: int = None) -> Iterator[Dict[str, Any]]:
        """Export raw Gmail messages from API."""
        pass
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """Process raw Gmail data into Document objects."""
        pass

class SlackExporter(BaseExporter):
    def export(self, channels: List[str] = None, days_ago: int = 7, limit: int = None) -> Iterator[Dict[str, Any]]:
        """Export raw Slack messages from API."""
        pass
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """Process raw Slack data into Document objects."""
        pass

class JiraExporter(BaseExporter):
    def export(self, project: str = None, status: str = None, assignee: str = None) -> Iterator[Dict[str, Any]]:
        """Export raw Jira issues from API."""
        pass
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """Process raw Jira data into Document objects."""
        pass
```

### Processing Functions (in exporters/__init__.py)
```python
def add_ingestion_timestamp(docs: Iterator[Document],
                          metadata_field: str = "ingestion_timestamp") -> Iterator[Document]:
    """Add timestamp to document metadata with configurable field name."""
    timestamp = datetime.now().isoformat()
    for doc in docs:
        if doc.metadata is None:
            doc.metadata = {}
        doc.metadata[metadata_field] = timestamp
        yield doc

def convert_to_ai_documents(docs: Iterator[Document], store_name: str) -> Iterator[AIDocument]:
    """Convert Documents to AIDocuments using the registry."""
    from prefect_data_getters.stores.document_registry import DocumentTypeRegistry
    
    for doc in docs:
        ai_doc = DocumentTypeRegistry.create_document({
            'page_content': doc.page_content,
            'metadata': doc.metadata or {},
            'id': getattr(doc, 'id', None)
        }, store_name)
        if hasattr(doc, 'id') and doc.id:
            ai_doc.id = doc.id
        yield ai_doc
```

## Usage Patterns (Enhanced with Separated Export/Process)

### Pattern 1: Separate Export and Process
```python
from prefect_data_getters.exporters.gmail_exporter import GmailExporter
from prefect_data_getters.exporters import add_ingestion_timestamp, convert_to_ai_documents

# Separate raw data export from processing
exporter = GmailExporter()

# Export raw Gmail API data
raw_messages = exporter.export(days_ago=7, query="from:important@company.com")

# Process raw data into documents
documents = exporter.process(raw_messages)

# Apply processing functions
processed = add_ingestion_timestamp(documents)
ai_docs = convert_to_ai_documents(processed, "email_messages")

# Storage using existing AIDocument methods
for doc in ai_docs:
    doc.save("email_messages", also_store_vectors=True)
```

### Pattern 2: Raw Data Analysis and Custom Processing
```python
from prefect_data_getters.exporters.gmail_exporter import GmailExporter

exporter = GmailExporter()

# Export raw data for analysis
raw_messages = exporter.export(days_ago=7)

# Analyze raw data before processing
important_messages = []
for msg in raw_messages:
    if 'IMPORTANT' in msg.get('labelIds', []):
        important_messages.append(msg)

# Process only important messages
documents = exporter.process(iter(important_messages))

# Custom processing
def custom_email_processor(docs: Iterator[Document]) -> Iterator[Document]:
    """Custom processing specific to your needs."""
    for doc in docs:
        if 'important' in doc.metadata.get('subject', '').lower():
            doc.metadata['priority'] = 'high'
        yield doc

custom_processed = custom_email_processor(documents)
ai_docs = convert_to_ai_documents(custom_processed, "email_messages")

# Use existing storage methods
for doc in ai_docs:
    doc.save("email_messages", also_store_vectors=True)
```

### Pattern 3: Backward Compatibility (Convenience Method)
```python
from prefect_data_getters.exporters.gmail_exporter import GmailExporter
from prefect_data_getters.exporters import add_ingestion_timestamp, convert_to_ai_documents

# Use convenience method for backward compatibility
exporter = GmailExporter()
documents = exporter.export_documents(days_ago=7)  # Combines export + process
processed = add_ingestion_timestamp(documents, metadata_field="processed_at")
ai_docs = convert_to_ai_documents(processed, "email_messages")

# Use existing storage methods
for doc in ai_docs:
    doc.save("email_messages", also_store_vectors=True)
```

### Pattern 4: Caching and Reprocessing
```python
from prefect_data_getters.exporters.slack_exporter import SlackExporter

exporter = SlackExporter()

# Export and cache raw data
raw_messages = list(exporter.export(channels=['general'], days_ago=7))

# Process with different strategies
strategy_1_docs = list(exporter.process(iter(raw_messages)))
strategy_2_docs = list(exporter.process(iter(raw_messages)))  # Different processing

# Raw data can be reused without re-calling APIs
```

## Code Style Guidelines

### File Size Limits
- **Maximum 500 lines per file** - refactor into modules if approaching this limit
- Split large exporters into separate authentication, extraction, and transformation modules

### Type Hints and Documentation
```python
from typing import Iterator, Optional, List
from langchain_core.documents import Document

def add_ingestion_timestamp(
    docs: Iterator[Document], 
    metadata_field: str = "ingestion_timestamp"
) -> Iterator[Document]:
    """
    Add timestamp to document metadata.
    
    Args:
        docs: Iterator of documents to process
        metadata_field: Name of metadata field to store timestamp
        
    Returns:
        Iterator of documents with timestamp metadata
        
    Yields:
        Document: Document with added timestamp metadata
    """
```

### Testing Requirements
- **Unit tests for all new functions and classes**
- Tests in `/tests` folder mirroring main structure
- Minimum test coverage:
  - 1 test for expected use
  - 1 edge case test
  - 1 failure case test

### Import Conventions
```python
# Always use absolute imports
from prefect_data_getters.exporters.base import BaseExporter
from prefect_data_getters.exporters import add_ingestion_timestamp, convert_to_ai_documents
from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.document_registry import DocumentTypeRegistry

# External packages
from langchain_core.documents import Document
from typing import Iterator, Optional
```

## Migration Strategy

### Phase 1: Create Base Infrastructure
1. Create `BaseExporter` abstract class
2. Create basic processing functions
3. Set up testing framework

### Phase 2: Refactor Existing Exporters
1. Refactor Gmail exporter to inherit from `BaseExporter`
2. Refactor Slack exporter
3. Refactor other exporters one by one

### Phase 3: Add Processing Functions
1. Extract common processing logic into functions
2. Create source-specific processing functions
3. Add convenience workflows

### Phase 4: Integration and Testing
1. Comprehensive integration testing
2. Performance testing
3. Documentation updates

## Dependencies

### Core Dependencies
- `langchain-core`: Document classes
- `pydantic`: Data validation
- `typing`: Type hints

### Data Source Dependencies
- `google-api-python-client`: Gmail API
- `slack-sdk`: Slack API
- `jira`: Jira API
- `elasticsearch`: Elasticsearch client

### Testing Dependencies
- `pytest`: Testing framework
- `pytest-mock`: Mocking utilities
- `black`: Code formatting

## Configuration Management

### Environment Variables
```python
# Use environment variables for configuration
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "secrets/google_app_creds.json")
```

### Configuration Classes
```python
from pydantic import BaseSettings

class ExporterConfig(BaseSettings):
    """Configuration for exporters."""
    batch_size: int = 100
    max_retries: int = 3
    timeout: int = 30
    
    class Config:
        env_prefix = "EXPORTER_"
```

## Performance Considerations

### Memory Efficiency
- Use iterators throughout to handle large datasets
- Process documents in streams rather than loading all into memory
- Implement batching for storage operations

### Error Handling
- Graceful degradation when individual documents fail
- Retry mechanisms for transient failures
- Comprehensive logging for debugging

## Security Considerations

### Credential Management
- Store credentials in secure locations
- Use environment variables for sensitive configuration
- Implement proper authentication refresh mechanisms

### Data Privacy
- Respect data retention policies
- Implement data anonymization where required
- Secure storage of processed documents

## Established Implementation Pattern (2025-06-13)

Based on the successful implementation of Gmail and Slack exporters, the following pattern has been established for all future exporters:

### Enhanced BaseExporter Pattern
The BaseExporter now requires two abstract methods:
- `export(**kwargs) -> Iterator[Any]` - Returns raw API data
- `process(raw_data: Iterator[Any]) -> Iterator[Document]` - Converts raw data to Documents
- `export_documents(**kwargs) -> Iterator[Document]` - Convenience method combining both

### File Structure Pattern
```
src/prefect_data_getters/exporters/
├── base.py                    # BaseExporter abstract class
├── {name}_exporter.py         # New exporter implementation
├── {name}/                    # Existing module (backward compatibility)
│   └── __init__.py           # Imports from new exporter + deprecation warnings
└── __init__.py               # Processing functions + exporter imports
```

### Implementation Benefits
1. **Clear Separation**: Raw data export vs. document processing
2. **Public Access**: Both export() and process() methods are public
3. **Debugging**: Can inspect raw API responses before processing
4. **Caching**: Can cache raw data and reprocess differently
5. **Testing**: Easy to mock raw data without API calls
6. **Flexibility**: Custom processing of raw data before document creation
7. **Backward Compatibility**: Existing code continues to work

### Implementation Checklist
For each new exporter:
- [ ] Create `{name}_exporter.py` with class inheriting from BaseExporter
- [ ] Implement `export()` method returning `Iterator[Dict[str, Any]]`
- [ ] Implement `process()` method returning `Iterator[Document]`
- [ ] Add authentication and error handling
- [ ] Create comprehensive test suite (20+ tests)
- [ ] Update backward compatibility in existing modules
- [ ] Add usage examples and documentation
- [ ] Verify 100% test pass rate

This enhanced architecture provides a solid foundation for a maintainable, extensible, and performant data ingestion system while maintaining loose coupling between components and enabling advanced use cases through raw data access.