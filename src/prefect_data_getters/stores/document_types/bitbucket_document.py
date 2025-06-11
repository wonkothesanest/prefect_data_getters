"""
Bitbucket document type implementation.
"""

from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.document_registry import register_document_type

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