"""
Jira exporter implementation using the BaseExporter architecture.

This module provides the JiraExporter class that inherits from BaseExporter,
implementing Jira-specific functionality for exporting issue documents.
"""

import logging
from datetime import datetime, timedelta
from typing import Iterator, Optional, Dict, Any, List

from langchain_core.documents import Document
from atlassian import Jira
from prefect.blocks.system import Secret
from tenacity import retry, stop_after_attempt, wait_fixed

from prefect_data_getters.exporters.base import BaseExporter
from prefect_data_getters.stores.document_types import JiraDocument


class JiraExporter(BaseExporter):
    """
    Jira exporter that inherits from BaseExporter.
    
    This class provides functionality to export Jira issues as Document objects,
    with support for authentication, JQL querying, and issue processing.
    
    Attributes:
        _client: Cached Jira client instance
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Jira exporter.
        
        Args:
            config: Optional configuration dictionary containing Jira-specific
                   settings such as credentials, server URL, etc.
        """
        super().__init__(config)
        self._client: Optional[Jira] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _get_jira_client(self) -> Jira:
        """
        Get authenticated Jira client instance.
        
        Returns:
            Jira: Authenticated Jira client
            
        Raises:
            Exception: If authentication fails or credentials are invalid
        """
        if self._client is None:
            try:
                # Try to get credentials from config first, then from Prefect Secret
                if self.config and all(k in self.config for k in ['username', 'api_token', 'url']):
                    username = self.config['username']
                    api_token = self.config['api_token']
                    url = self.config['url']
                else:
                    # Fallback to Prefect Secret
                    secret_block = Secret.load("jira-credentials")
                    secret = secret_block.get()
                    username = secret["username"]
                    api_token = secret["api-token"]
                    url = secret["url"]
                
                self._client = Jira(
                    url=url,
                    username=username,
                    password=api_token
                )
                
                self.logger.info("Successfully authenticated with Jira")
                
            except Exception as e:
                self.logger.error(f"Failed to authenticate with Jira: {e}")
                raise
        
        return self._client
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def export(
        self,
        projects: Optional[str | List[str]] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        days_ago: int = 30
    ) -> Iterator[Dict[str, Any]]:
        """
        Export raw Jira issues from the API.
        
        Args:
            project: Project key(s) to filter issues. Can be a single project key (e.g., 'PROJ')
                    or a list of project keys (e.g., ['PROJ1', 'PROJ2'])
            status: Status to filter issues (e.g., 'Open', 'In Progress')
            assignee: Assignee username to filter issues
            days_ago: Number of days back to search for issues
            
        Returns:
            Iterator[Dict[str, Any]]: Iterator yielding raw Jira issue data
            
        Raises:
            Exception: If API call fails or authentication is invalid
        """
        try:
            client = self._get_jira_client()
            
            # Build JQL query based on parameters
            jql_parts = []
            
            if projects:
                if isinstance(projects, list):
                    # Handle list of projects
                    if len(projects) == 1:
                        jql_parts.append(f'project = "{projects[0]}"')
                    else:
                        project_list = ', '.join(f'"{p}"' for p in projects)
                        jql_parts.append(f'project in ({project_list})')
                else:
                    # Handle single project string
                    jql_parts.append(f'project = "{projects}"')
            
            if status:
                jql_parts.append(f'status = "{status}"')
            
            if assignee:
                jql_parts.append(f'assignee = "{assignee}"')
            
            # Add date filter
            if days_ago > 0:
                date_threshold = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
                jql_parts.append(f'updated >= "{date_threshold}"')
            
            jql_query = ' AND '.join(jql_parts) if jql_parts else 'updated >= -30d'
            
            self.logger.info(f"Executing JQL query: {jql_query}")
            
            # Get issues with pagination
            start_at = 0
            max_results = 50
            total_issues = 0
            
            while True:
                try:
                    # Use JQL search with expanded fields
                    response = client.jql(
                        jql_query,
                        start=start_at,
                        limit=max_results,
                        expand='changelog,comments'
                    )
                    
                    issues = response.get('issues', [])
                    
                    if not issues:
                        break
                    
                    for issue in issues:
                        total_issues += 1
                        self.logger.debug(f"Yielding issue: {issue.get('key', 'Unknown')}")
                        yield issue
                    
                    # Check if we have more issues to fetch
                    if len(issues) < max_results:
                        break
                    
                    start_at += max_results
                    
                except Exception as e:
                    self.logger.error(f"Error fetching issues at offset {start_at}: {e}")
                    raise
            
            self.logger.info(f"Successfully exported {total_issues} Jira issues")
            
        except Exception as e:
            self.logger.error(f"Failed to export Jira issues: {e}")
            raise
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[JiraDocument]:
        """
        Process raw Jira issue data into Document objects.
        
        Args:
            raw_data: Iterator of raw Jira issue dictionaries from export()
            
        Returns:
            Iterator[Document]: Iterator yielding processed Document objects
        """
        for issue in raw_data:
            try:
                document = self._format_issue_to_document(issue)
                self.logger.debug(f"Processed issue: {document.metadata.get('key', 'Unknown')}")
                yield document
            except Exception as e:
                issue_key = issue.get('key', 'Unknown')
                self.logger.error(f"Failed to process issue {issue_key}: {e}")
                # Continue processing other issues
                continue
    
    def _format_issue_to_document(self, issue: Dict[str, Any]) -> JiraDocument:
        """
        Convert a raw Jira issue to a Document object.
        
        Args:
            issue: Raw Jira issue dictionary from API
            
        Returns:
            Document: Processed document with content and metadata
        """
        # Use issue key as the document ID
        doc_id = issue.get('key', '')
        
        # Extract summary and description for the content
        fields = issue.get('fields', {})
        summary = fields.get('summary', '')
        description = fields.get('description', '')
        content = f"{summary}\n\n{description}\n\n"
        
        # Flatten metadata using the same field extraction logic as the original
        metadata = {'key': doc_id}
        
        # Define desired fields to extract
        desired_fields = [
            'statuscategorychangedate',
            'priority.name',
            'status.name',
            'status.statusCategory.name',
            'creator.displayName',
            'reporter.displayName',
            'assignee.displayName',
            'issuetype.name',
            'issuetype.description',
            'issuetype.subtask',
            'issuetype.hierarchyLevel',
            'project.name',
            'project.key',
            'resolutiondate',
            'watches.watchCount',
            'watches.isWatching',
            'created',
            'updated',
            'comment.comments',
        ]
        
        for field in desired_fields:
            if field == 'comment.comments':
                # Handle comments
                comments = self._get_issue_value(issue, 'fields.comment.comments') or []
                first_comment = True
                for comment in comments:
                    author_name = self._get_issue_value(comment, 'author.displayName')
                    body = self._get_issue_value(comment, 'body')
                    comment_text = f"{author_name}: {body}"
                    if first_comment:
                        content += "########## Comments ##########\n"
                        first_comment = False
                    content += comment_text + "\n\n"
            elif field in ["created", "updated"]:
                value = self._get_issue_value(issue, f'fields.{field}')
                try:
                    # Convert to timestamp for easier querying
                    ts_value = datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
                    metadata[f"{field.replace('.', '_')}_ts"] = ts_value
                    metadata[field.replace('.', '_')] = value
                except (ValueError, AttributeError):
                    # If date parsing fails, just store the original value
                    if value:
                        metadata[field.replace('.', '_')] = value
            else:
                value = self._get_issue_value(issue, f'fields.{field}')
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value)
                elif isinstance(value, dict):
                    value = str(value)
                if value is not None:
                    metadata[field.replace('.', '_')] = value
        
        # Ensure metadata is clean and serializable
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        document = JiraDocument(id=doc_id, page_content=content, metadata=metadata)
        return document
    
    def _get_issue_value(self, issue: Dict[str, Any], field_path: str) -> Any:
        """
        Extract value from issue dict using dot-separated field path.
        
        Args:
            issue: Issue dictionary
            field_path: Dot-separated path to the field (e.g., 'fields.priority.name')
            
        Returns:
            Any: The extracted value or None if not found
        """
        fields = field_path.split('.')
        value = issue
        
        for field in fields:
            if isinstance(value, dict):
                value = value.get(field, None)
            elif isinstance(value, list) and field.isdigit():
                index = int(field)
                if index < len(value):
                    value = value[index]
                else:
                    value = None
            else:
                value = None
            
            if value is None:
                break
        
        return value