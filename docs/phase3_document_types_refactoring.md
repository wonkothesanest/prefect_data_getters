# Phase 3: Document Types Refactoring

## Overview

This phase migrates individual document type classes to use the new AIDocument base class and registry pattern, eliminating wrapper complexity and simplifying the document type implementations.

## Goals

1. **Migrate document subclasses** to inherit from new AIDocument
2. **Organize document types** into separate files for better maintainability
3. **Register document types** using the registry pattern
4. **Simplify `__str__` methods** using the base formatter
5. **Eliminate `_type_name` usage** in favor of `__class__.__name__`
6. **Maintain all existing functionality** while improving code structure

## Prerequisites

- Phase 1 must be completed (new AIDocument base class)
- Phase 2 must be completed (document registry)
- All previous phase tests must be passing

## Current State Analysis

### Problems to Solve
- Document types scattered in single large file
- Repetitive `__str__` method implementations
- Manual `_type_name` management
- Wrapper pattern complexity in constructors
- Inconsistent ID handling across document types

### Current Document Structure Example (JiraDocument)
```python
class JiraDocument(AIDocument):
    def __init__(self, doc):
        super().__init__(doc)                    # ← Wrapper pattern
        self._type_name = "Jira Document"        # ← Manual type name
        self.id = self._get_metadata("key")      # ← Manual ID extraction

    def __str__(self):                           # ← Repetitive formatting
        s = f"""
{super().__str__()}
Jira Key: {self._get_metadata("key")}
Issue Type: {self._get_metadata("issuetype_name")}
# ... lots of boilerplate formatting
"""
        return s
```

## Implementation Plan

### Step 1: Create Document Types Directory Structure

```
src/prefect_data_getters/stores/document_types/
├── __init__.py
├── jira_document.py
├── email_document.py
├── slack_document.py
├── slab_document.py
└── bitbucket_document.py
```

### Step 2: Migrate JiraDocument

**File**: `src/prefect_data_getters/stores/document_types/jira_document.py`

```python
"""
Jira document type implementation.
"""

from ..documents_new import AIDocument
from ..document_registry import register_document_type
from typing import Optional

@register_document_type("jira_issues")
class JiraDocument(AIDocument):
    """Document type for Jira issues with Jira-specific functionality."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize JiraDocument.
        
        Args:
            page_content: The main content of the Jira issue
            metadata: Dictionary containing Jira issue metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
    
    def get_display_id(self) -> str:
        """Override to use Jira key as display ID"""
        return self.jira_key or "Unknown"
    
    # Jira-specific properties for easy access
    @property
    def jira_key(self) -> str:
        """Get the Jira issue key (e.g., PROJ-123)"""
        return self._get_metadata("key", "")
    
    @property
    def issue_type(self) -> str:
        """Get the Jira issue type (e.g., Bug, Story, Epic)"""
        return self._get_metadata("issuetype_name", "")
    
    @property
    def status(self) -> str:
        """Get the current status of the Jira issue"""
        return self._get_metadata("status_name", "")
    
    @property
    def priority(self) -> str:
        """Get the priority of the Jira issue"""
        return self._get_metadata("priority_name", "")
    
    @property
    def assignee(self) -> str:
        """Get the assignee of the Jira issue"""
        return self._get_metadata("assignee_name", "")
    
    @property
    def reporter(self) -> str:
        """Get the reporter of the Jira issue"""
        return self._get_metadata("reporter_name", "")
    
    @property
    def created_date(self) -> str:
        """Get the creation date of the Jira issue"""
        return self._get_metadata("created", "")
    
    @property
    def updated_date(self) -> str:
        """Get the last updated date of the Jira issue"""
        return self._get_metadata("updated", "")
    
    @property
    def resolution_date(self) -> Optional[str]:
        """Get the resolution date of the Jira issue (if resolved)"""
        return self._get_metadata("resolutiondate")
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "Jira Key": self.jira_key,
            "Issue Type": self.issue_type,
            "Status": self.status,
            "Priority": self.priority,
            "Assignee": self.assignee,
            "Reporter": self.reporter,
            "Created Date": self.created_date,
            "Updated Date": self.updated_date,
            "Resolution Date": self.resolution_date
        })
```

### Step 3: Migrate EmailDocument

**File**: `src/prefect_data_getters/stores/document_types/email_document.py`

```python
"""
Email document type implementation.
"""

from ..documents_new import AIDocument
from ..document_registry import register_document_type

@register_document_type("email_messages")
class EmailDocument(AIDocument):
    """Document type for email messages with email-specific functionality."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize EmailDocument.
        
        Args:
            page_content: The main content of the email
            metadata: Dictionary containing email metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
    
    def get_display_id(self) -> str:
        """Override to use message ID as display ID"""
        return self.message_id or "Unknown"
    
    # Email-specific properties
    @property
    def message_id(self) -> str:
        """Get the email message ID"""
        return self._get_metadata("message-id", "")
    
    @property
    def sender(self) -> str:
        """Get the email sender"""
        return self._get_metadata("from", "")
    
    @property
    def recipients(self) -> str:
        """Get the email recipients"""
        return self._get_metadata("to", "")
    
    @property
    def subject(self) -> str:
        """Get the email subject"""
        return self._get_metadata("subject", "")
    
    @property
    def date(self) -> str:
        """Get the email date"""
        return self._get_metadata("date", "")
    
    @property
    def cc(self) -> str:
        """Get the CC recipients"""
        return self._get_metadata("cc", "")
    
    @property
    def bcc(self) -> str:
        """Get the BCC recipients"""
        return self._get_metadata("bcc", "")
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "Message ID": self.message_id,
            "From": self.sender,
            "To": self.recipients,
            "CC": self.cc,
            "Subject": self.subject,
            "Date": self.date
        })
```

### Step 4: Migrate SlackMessageDocument

**File**: `src/prefect_data_getters/stores/document_types/slack_document.py`

```python
"""
Slack document type implementation.
"""

from ..documents_new import AIDocument
from ..document_registry import register_document_type
from datetime import datetime

@register_document_type("slack_messages")
class SlackMessageDocument(AIDocument):
    """Document type for Slack messages with Slack-specific functionality."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize SlackMessageDocument.
        
        Args:
            page_content: The main content of the Slack message
            metadata: Dictionary containing Slack message metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
    
    def get_display_id(self) -> str:
        """Override to use channel_timestamp as display ID"""
        channel = self.channel
        timestamp = self.timestamp
        if channel and timestamp:
            return f"{channel}_{timestamp}"
        return "Unknown"
    
    # Slack-specific properties
    @property
    def user(self) -> str:
        """Get the Slack user who sent the message"""
        return self._get_metadata("user", "")
    
    @property
    def channel(self) -> str:
        """Get the Slack channel where the message was sent"""
        return self._get_metadata("channel", "")
    
    @property
    def timestamp(self) -> str:
        """Get the raw timestamp of the message"""
        return self._get_metadata("ts", "")
    
    @property
    def formatted_timestamp(self) -> str:
        """Get the formatted timestamp of the message"""
        timestamp = self._get_metadata("ts")
        if timestamp:
            try:
                return datetime.fromtimestamp(float(timestamp)).isoformat()
            except (ValueError, TypeError):
                return str(timestamp)
        return "N/A"
    
    @property
    def thread_ts(self) -> str:
        """Get the thread timestamp if this is a threaded message"""
        return self._get_metadata("thread_ts", "")
    
    @property
    def is_thread_reply(self) -> bool:
        """Check if this message is a reply in a thread"""
        return bool(self.thread_ts)
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "User": self.user,
            "Channel": self.channel,
            "Timestamp": self.formatted_timestamp,
            "Thread Reply": "Yes" if self.is_thread_reply else "No"
        })
```

### Step 5: Migrate SlabDocument and SlabChunkDocument

**File**: `src/prefect_data_getters/stores/document_types/slab_document.py`

```python
"""
Slab document type implementations.
"""

from ..documents_new import AIDocument
from ..document_registry import register_document_type
import uuid

@register_document_type("slab_documents")
class SlabDocument(AIDocument):
    """Document type for Slab documents with Slab-specific functionality."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize SlabDocument.
        
        Args:
            page_content: The main content of the Slab document
            metadata: Dictionary containing Slab document metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
    
    def get_display_id(self) -> str:
        """Override to use document ID as display ID"""
        return self.document_id or "Unknown"
    
    # Slab-specific properties
    @property
    def document_id(self) -> str:
        """Get the Slab document ID"""
        return self._get_metadata("document_id", "")
    
    @property
    def title(self) -> str:
        """Get the Slab document title"""
        return self._get_metadata("title", "")
    
    @property
    def owner(self) -> str:
        """Get the Slab document owner"""
        return self._get_metadata("owner", "")
    
    @property
    def contributors(self) -> str:
        """Get the Slab document contributors"""
        return self._get_metadata("contributors", "")
    
    @property
    def topics(self) -> str:
        """Get the Slab document topics/tags"""
        return self._get_metadata("topics", "")
    
    @property
    def doc_type(self) -> str:
        """Get the Slab document type"""
        return self._get_metadata("type", "slab_document")
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "Document ID": self.document_id,
            "Title": self.title,
            "Type": self.doc_type,
            "Owner": self.owner,
            "Contributors": self.contributors,
            "Topics": self.topics
        })

@register_document_type("slab_document_chunks")
class SlabChunkDocument(SlabDocument):
    """Document type for Slab document chunks."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize SlabChunkDocument.
        
        Args:
            page_content: The main content of the Slab document chunk
            metadata: Dictionary containing Slab document metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
        
        # Generate unique ID for chunk if not provided
        if not hasattr(self, 'id') or not self.id:
            self.id = str(uuid.uuid4())
    
    def get_display_id(self) -> str:
        """Override to use generated UUID as display ID"""
        return getattr(self, 'id', str(uuid.uuid4()))
    
    @property
    def doc_type(self) -> str:
        """Get the document type (overridden for chunks)"""
        return self._get_metadata("type", "slab_chunk")
    
    @property
    def parent_document_id(self) -> str:
        """Get the parent document ID this chunk belongs to"""
        return self.document_id
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "Chunk ID": self.get_display_id(),
            "Parent Document ID": self.parent_document_id,
            "Title": self.title,
            "Type": self.doc_type,
            "Owner": self.owner,
            "Contributors": self.contributors,
            "Topics": self.topics
        })
```

### Step 6: Migrate BitbucketPR

**File**: `src/prefect_data_getters/stores/document_types/bitbucket_document.py`

```python
"""
Bitbucket document type implementation.
"""

from ..documents_new import AIDocument
from ..document_registry import register_document_type

@register_document_type("bitbucket_pull_requests")
class BitbucketPR(AIDocument):
    """Document type for Bitbucket pull requests with PR-specific functionality."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize BitbucketPR.
        
        Args:
            page_content: The main content of the pull request
            metadata: Dictionary containing PR metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {})
    
    def get_display_id(self) -> str:
        """Override to use PR ID as display ID"""
        return self.pr_id or "Unknown"
    
    # Bitbucket PR-specific properties
    @property
    def pr_id(self) -> str:
        """Get the pull request ID"""
        return self._get_metadata("id", "")
    
    @property
    def repository(self) -> str:
        """Get the repository slug"""
        return self._get_metadata("repo_slug", "")
    
    @property
    def title(self) -> str:
        """Get the pull request title"""
        return self._get_metadata("title", "")
    
    @property
    def author(self) -> str:
        """Get the pull request author"""
        return self._get_metadata("author_name", "")
    
    @property
    def participants(self) -> str:
        """Get all participants in the pull request"""
        return self._get_metadata("all_participants", "")
    
    @property
    def source_branch(self) -> str:
        """Get the source branch"""
        return self._get_metadata("source_branch", "")
    
    @property
    def destination_branch(self) -> str:
        """Get the destination branch"""
        return self._get_metadata("destination_branch", "")
    
    @property
    def state(self) -> str:
        """Get the pull request state"""
        return self._get_metadata("state", "")
    
    @property
    def created_date(self) -> str:
        """Get the creation date"""
        return self._get_metadata("created_on", "")
    
    @property
    def updated_date(self) -> str:
        """Get the last updated date"""
        return self._get_metadata("updated_on", "")
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "PR ID": self.pr_id,
            "Repository": self.repository,
            "Title": self.title,
            "Author": self.author,
            "Participants": self.participants,
            "Source Branch": self.source_branch,
            "Destination Branch": self.destination_branch,
            "State": self.state,
            "Created": self.created_date,
            "Updated": self.updated_date
        })
```

### Step 7: Create Document Types Package Init

**File**: `src/prefect_data_getters/stores/document_types/__init__.py`

```python
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
```

### Step 8: Create Phase 3 Tests

**File**: `src/prefect_data_getters/test/test_phase3_document_types.py`

```python
import pytest
from ..stores.document_types.jira_document import JiraDocument
from ..stores.document_types.email_document import EmailDocument
from ..stores.document_types.slack_document import SlackMessageDocument
from ..stores.document_types.slab_document import SlabDocument, SlabChunkDocument
from ..stores.document_types.bitbucket_document import BitbucketPR
from ..stores.document_registry import DocumentTypeRegistry

class TestPhase3DocumentTypes:
    """Test suite for Phase 3 document type refactoring"""
    
    def test_jira_document_properties(self):
        """Test JiraDocument specific properties and functionality"""
        metadata = {
            "key": "PROJ-123",
            "issuetype_name": "Bug",
            "status_name": "Open",
            "priority_name": "High",
            "assignee_name": "John Doe",
            "reporter_name": "Jane Smith",
            "created": "2023-01-01T00:00:00Z",
            "updated": "2023-01-02T00:00:00Z",
            "resolutiondate": "2023-01-03T00:00:00Z"
        }
        
        doc = JiraDocument("Jira issue content", metadata)
        
        assert doc.document_type == "JiraDocument"
        assert doc.jira_key == "PROJ-123"
        assert doc.issue_type == "Bug"
        assert doc.status == "Open"
        assert doc.priority == "High"
        assert doc.assignee == "John Doe"
        assert doc.reporter == "Jane Smith"
        assert doc.get_display_id() == "PROJ-123"
        
        # Test string representation
        str_repr = str(doc)
        assert "Document Type: JiraDocument" in str_repr
        assert "Jira Key: PROJ-123" in str_repr
        assert "Issue Type: Bug" in str_repr
    
    def test_email_document_properties(self):
        """Test EmailDocument specific properties and functionality"""
        metadata = {
            "message-id": "msg-123",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "subject": "Test Email",
            "date": "2023-01-01T00:00:00Z",
            "cc": "cc@example.com"
        }
        
        doc = EmailDocument("Email content", metadata)
        
        assert doc.document_type == "EmailDocument"
        assert doc.message_id == "msg-123"
        assert doc.sender == "sender@example.com"
        assert doc.recipients == "recipient@example.com"
        assert doc.subject == "Test Email"
        assert doc.get_display_id() == "msg-123"
    
    def test_slack_document_properties(self):
        """Test SlackMessageDocument specific properties and functionality"""
        metadata = {
            "user": "john.doe",
            "channel": "general",
            "ts": "1640995200.000000",  # Unix timestamp
            "thread_ts": "1640995100.000000"
        }
        
        doc = SlackMessageDocument("Slack message content", metadata)
        
        assert doc.document_type == "SlackMessageDocument"
        assert doc.user == "john.doe"
        assert doc.channel == "general"
        assert doc.timestamp == "1640995200.000000"
        assert doc.is_thread_reply == True
        assert doc.get_display_id() == "general_1640995200.000000"
        
        # Test formatted timestamp
        assert "2022-01-01" in doc.formatted_timestamp
    
    def test_slab_document_properties(self):
        """Test SlabDocument specific properties and functionality"""
        metadata = {
            "document_id": "slab-123",
            "title": "Test Document",
            "owner": "John Doe",
            "contributors": "Jane Smith, Bob Johnson",
            "topics": "engineering, documentation",
            "type": "specification"
        }
        
        doc = SlabDocument("Slab document content", metadata)
        
        assert doc.document_type == "SlabDocument"
        assert doc.document_id == "slab-123"
        assert doc.title == "Test Document"
        assert doc.owner == "John Doe"
        assert doc.doc_type == "specification"
        assert doc.get_display_id() == "slab-123"
    
    def test_slab_chunk_document_properties(self):
        """Test SlabChunkDocument specific properties and functionality"""
        metadata = {
            "document_id": "slab-123",
            "title": "Test Document",
            "owner": "John Doe"
        }
        
        doc = SlabChunkDocument("Slab chunk content", metadata)
        
        assert doc.document_type == "SlabChunkDocument"
        assert doc.parent_document_id == "slab-123"
        assert doc.doc_type == "slab_chunk"
        assert doc.get_display_id() != "Unknown"  # Should have generated UUID
        assert len(doc.get_display_id()) == 36  # UUID length
    
    def test_bitbucket_pr_properties(self):
        """Test BitbucketPR specific properties and functionality"""
        metadata = {
            "id": "pr-123",
            "repo_slug": "my-repo",
            "title": "Fix bug in authentication",
            "author_name": "John Doe",
            "source_branch": "feature/auth-fix",
            "destination_branch": "main",
            "state": "OPEN",
            "created_on": "2023-01-01T00:00:00Z"
        }
        
        doc = BitbucketPR("PR description content", metadata)
        
        assert doc.document_type == "BitbucketPR"
        assert doc.pr_id == "pr-123"
        assert doc.repository == "my-repo"
        assert doc.title == "Fix bug in authentication"
        assert doc.author == "John Doe"
        assert doc.state == "OPEN"
        assert doc.get_display_id() == "pr-123"
    
    def test_document_registry_integration(self):
        """Test that all document types are properly registered"""
        # Import the package to trigger registration
        import prefect_data_getters.stores.document_types
        
        registered_types = DocumentTypeRegistry.list_registered_types()
        
        assert "jira_issues" in registered_types
        assert "email_messages" in registered_types
        assert "slack_messages" in registered_types
        assert "slab_documents" in registered_types
        assert "slab_document_chunks" in registered_types
        assert "bitbucket_pull_requests" in registered_types
        
        # Test document creation through registry
        jira_data = {
            'page_content': 'test content',
            'metadata': {'key': 'TEST-123'},
            'id': 'TEST-123'
        }
        
        doc = DocumentTypeRegistry.create_document(jira_data, "jira_issues")
        assert isinstance(doc, JiraDocument)
        assert doc.jira_key == "TEST-123"
```

## Migration Steps

### Step 1: Create Directory Structure
1. Create `document_types/` directory
2. Create `__init__.py` file

### Step 2: Migrate Document Types One by One
1. Start with JiraDocument (most complex)
2. Migrate EmailDocument
3. Migrate SlackMessageDocument
4. Migrate SlabDocument and SlabChunkDocument
5. Migrate BitbucketPR

### Step 3: Update Registry Integration
1. Ensure all document types are registered
2. Update registry to import document types
3. Test registry functionality

### Step 4: Validation
1. Run all tests to ensure functionality preserved
2. Test string representations
3. Verify all properties work correctly
4. Test registry integration

## Success Criteria

- [ ] All document types migrated to new base class
- [ ] All document types properly registered
- [ ] Document types organized in separate files
- [ ] All existing functionality preserved
- [ ] String representations simplified and consistent
- [ ] All tests pass
- [ ] No `_type_name` usage remaining
- [ ] Properties provide easy access to metadata

## Files Modified/Created

### New Files
- `src/prefect_data_getters/stores/document_types/__init__.py`
- `src/prefect_data_getters/stores/document_types/jira_document.py`
- `src/prefect_data_getters/stores/document_types/email_document.py`
- `src/prefect_data_getters/stores/document_types/slack_document.py`
- `src/prefect_data_getters/stores/document_types/slab_document.py`
- `src/prefect_data_getters/stores/document_types/bitbucket_document.py`
- `src/prefect_data_getters/test/test_phase3_document_types.py`

### Files to Update Later
- `src/prefect_data_getters/stores/documents.py` (deprecate old classes)
- Consumer files (in Phase 4)

## Next Phase

After Phase 3 is complete, proceed to **Phase 4: Elasticsearch Integration** which will implement the unified storage layer and integrate Elasticsearch operations directly into the document classes.

## Rollback Plan

If issues arise:
1. New document types are in separate files - easy to isolate
2. Registry pattern allows fallback to base AIDocument
3. Old document classes remain untouched during this phase
4. Can selectively rollback individual document types
5. Remove new files to completely rollback