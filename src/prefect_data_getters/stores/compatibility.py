"""
Backward compatibility layer to ease migration from old AIDocument to new one.
This file should be removed after migration is complete.
"""

from langchain_core.documents import Document
from .documents_new import AIDocument as NewAIDocument
from .documents import AIDocument as OldAIDocument
from ..utilities.constants import VECTOR_STORE_NAMES

class DocumentMigrationHelper:
    """Helper class to migrate between old and new document formats"""
    
    @staticmethod
    def convert_old_to_new(old_doc: OldAIDocument) -> NewAIDocument:
        """Convert old AIDocument to new AIDocument"""
        new_doc = NewAIDocument(
            page_content=old_doc.page_content,
            metadata=old_doc._document.metadata or {}
        )
        new_doc.search_score = old_doc.search_score
        if hasattr(old_doc, 'id') and old_doc.id:
            new_doc.id = old_doc.id
        return new_doc
    
    @staticmethod
    def convert_document_to_new(doc: Document) -> NewAIDocument:
        """Convert base Document to new AIDocument"""
        # Use **kwargs to properly pass metadata
        new_doc = NewAIDocument(
            page_content=doc.page_content,
            **({'metadata': doc.metadata} if doc.metadata else {})
        )
        if hasattr(doc, 'id') and doc.id:
            new_doc.id = doc.id
        return new_doc
    
    @staticmethod
    def batch_convert_documents(docs: list[Document]) -> list[NewAIDocument]:
        """Convert a list of Documents to new AIDocuments"""
        return [DocumentMigrationHelper.convert_document_to_new(doc) for doc in docs]