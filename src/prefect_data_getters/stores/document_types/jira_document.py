"""
Jira document type implementation.
"""

from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.document_registry import register_document_type
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