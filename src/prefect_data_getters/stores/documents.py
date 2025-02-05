import pprint
from langchain_core.documents import Document
from datetime import datetime
from typing import Literal
from prefect_data_getters.utilities.constants import VECTOR_STORE_NAMES  
import uuid


class _AIDocument:
    def __init__(self, doc: Document):
        self._document = doc
        self._type_name = None
        self.id = self._document.id
        self.page_content = self._document.page_content
        self.search_score = None
    
    def set_page_content(self, content: str) -> None:
        self._document.page_content = content
        self.page_content = content


    def _get_metadata(self, key, default=None):
        """Safely get a metadata value by key, returning `default` if it doesn't exist."""
        return self._document.metadata.get(key, default) if self._document.metadata else default

    def __str__(self):
        if self._type_name is None:
            raise NotImplementedError(self._document)
        else:
            return f"Document Type: {self._type_name}"

    def _context_section(self):
        """Returns the context section if present in the metadata."""
        context = self._get_metadata("context")
        if context:
            return f"""Context:
>>>>>>>>>>>>
{context}
>>>>>>>>>>>>
"""
        return ""

def _create_document(doc: Document, name: VECTOR_STORE_NAMES) -> _AIDocument:
    """Factory function to create a document instance based on the vector store name."""
    if name == "jira_issues":
        return JiraDocument(doc)
    elif name == "email_messages":
        return EmailDocument(doc)
    elif name == "slack_messages":
        return SlackMessageDocument(doc)
    elif name == "slab_documents":
        return SlabDocument(doc)
    elif name == "slab_document_chunks":
        return SlabChunkDocument(doc)
    elif name == "bitbucket_pull_requests":
        return BitbucketPR(doc=doc)
    else:
        # Although we’ve covered all Literal options, this serves as a safeguard
        raise ValueError(f"Unknown document type: {name}")
    

def convert_documents_to_ai_documents(docs: list[Document], doc_store_name: VECTOR_STORE_NAMES) -> list[_AIDocument]:
    return [_create_document(d, doc_store_name) for d in docs]

class JiraDocument(_AIDocument):
    def __init__(self, doc):
        super().__init__(doc)
        self._type_name = "Jira Document"
        self.id = self._get_metadata("key")

    def __str__(self):
        s = f"""
{super().__str__()}
Jira Key: {self._get_metadata("key")}
Issue Type: {self._get_metadata("issuetype_name")}
Status: {self._get_metadata("status_name")}
Priority: {self._get_metadata("priority_name")}
Created Date: {self._get_metadata("created")}
Updated Date: {self._get_metadata("updated")}
Resolution Date: {self._get_metadata("resolutiondate")}
Content:
>>>>>>>>>>>>
{self._document.page_content}
>>>>>>>>>>>>
{self._context_section()}
Additional Metadata:
{pprint.pformat(self._document.metadata)}
END: {self._get_metadata("key")}
>>>>>>>>>>>>
"""
        return s

class EmailDocument(_AIDocument):
    def __init__(self, doc):
        super().__init__(doc)
        self._type_name = "Email Document"
        self.id = self._get_metadata("message-id")

    def __str__(self):
        s = f"""
{super().__str__()}
Message ID: {self._get_metadata("message-id")}
From: {self._get_metadata("from")}
To: {self._get_metadata("to")}
Subject: {self._get_metadata("subject")}
Date: {self._get_metadata("date")}
Content:
>>>>>>>>>>>>
{self._document.page_content}
>>>>>>>>>>>>
{self._context_section()}
Additional Metadata:
{pprint.pformat(self._document.metadata)}
END: {self._get_metadata("message-id")}
>>>>>>>>>>>>
"""
        return s

class SlackMessageDocument(_AIDocument):
    def __init__(self, doc):
        super().__init__(doc)
        self._type_name = "Slack Message Document"
        self.id = f"{self._get_metadata("channel")}_{self._get_metadata("ts")}"

    def __str__(self):
        timestamp = self._get_metadata("ts")
        formatted_timestamp = datetime.fromtimestamp(timestamp).isoformat() if timestamp else "N/A"
        
        s = f"""
{super().__str__()}
User: {self._get_metadata("user")}
Channel: {self._get_metadata("channel")}
Timestamp: {formatted_timestamp}
Content:
>>>>>>>>>>>>
{self._document.page_content}
>>>>>>>>>>>>
{self._context_section()}
Additional Metadata:
{pprint.pformat(self._document.metadata)}
END: {self._get_metadata("user")}
>>>>>>>>>>>>
"""
        return s

class SlabDocument(_AIDocument):
    def __init__(self, doc):
        super().__init__(doc)
        self.id = self._get_metadata("document_id")
        self._type_name = "Slab Document"

    def __str__(self):
        s = f"""
{super().__str__()}
Document ID: {self._get_metadata("document_id")}
Title: {self._get_metadata("title")}
Type: {self._get_metadata("type", "slab_document")}
Owner: {self._get_metadata("owner")}
Contributors: {self._get_metadata("contributors")}
Topics: {self._get_metadata("topics")}
Content:
>>>>>>>>>>>>
{self._document.page_content}
>>>>>>>>>>>>
{self._context_section()}
Additional Metadata:
{pprint.pformat(self._document.metadata)}
END: {self._get_metadata("document_id")}
>>>>>>>>>>>>
"""
        return s

class SlabChunkDocument(SlabDocument):
    def __init__(self, doc):
        super().__init__(doc)
        self._type_name = "Slab Chunk Document"
        #TODO: using a guid for now but this will not allow us to get the original document from ES.
        self.id = str(uuid.uuid1())

    def __str__(self):
        s = f"""
{super().__str__()}
Document ID: {self._get_metadata("document_id")}
Title: {self._get_metadata("title")}
Type: {self._get_metadata("type", "slab_chunk")}
Owner: {self._get_metadata("owner")}
Contributors: {self._get_metadata("contributors")}
Topics: {self._get_metadata("topics")}
Content:
>>>>>>>>>>>>
{self._document.page_content}
>>>>>>>>>>>>
{self._context_section()}
Additional Metadata:
{pprint.pformat(self._document.metadata)}
END: {self._get_metadata("document_id")}
>>>>>>>>>>>>
"""
        return s


class BitbucketPR(_AIDocument):
    def __init__(self, doc):
        super().__init__(doc)
        self.id = self._get_metadata("id")
        self._type_name = "Bitbucket Pull Request"

    def __str__(self):
        s = f"""
{super().__str__()}
Document ID: {self._get_metadata("id")}
Repository: {self._get_metadata("repo_slug")}
Title: {self._get_metadata("title")}
Type: {self._type_name}
Author: {self._get_metadata("author_name")}
Contributors: {self._get_metadata("all_participants")}
Source Branch: {self._get_metadata("source_branch")}
Destination Branch: {self._get_metadata("destination_branch")}
Pull Request Status: {self._get_metadata("state")}
Content:
>>>>>>>>>>>>
{self._document.page_content}
>>>>>>>>>>>>
{self._context_section()}
Additional Metadata:
{pprint.pformat(self._document.metadata)}
END: {self._get_metadata("document_id")}
>>>>>>>>>>>>
"""
        return s