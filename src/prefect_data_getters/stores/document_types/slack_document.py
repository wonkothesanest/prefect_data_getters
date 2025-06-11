"""
Slack document type implementation.
"""

from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.document_registry import register_document_type
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