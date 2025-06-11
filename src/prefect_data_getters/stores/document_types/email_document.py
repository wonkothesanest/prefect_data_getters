"""
Email document type implementation.
"""

from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.document_registry import register_document_type

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