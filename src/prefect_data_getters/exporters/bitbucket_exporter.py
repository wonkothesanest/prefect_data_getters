"""
Bitbucket exporter implementation using the BaseExporter architecture.

This module provides the BitbucketExporter class that inherits from BaseExporter,
implementing Bitbucket-specific functionality for exporting pull request documents.
"""

from datetime import datetime, timedelta
from typing import Iterator, Optional, Dict, Any, List

from langchain_core.documents import Document
from tenacity import retry, stop_after_attempt, wait_fixed

from prefect_data_getters.exporters.base import BaseExporter
from datetime import datetime
from atlassian import Bitbucket
from atlassian.bitbucket import Cloud
from prefect.blocks.system import Secret

from prefect_data_getters.stores.document_types.bitbucket_document import BitbucketPR


class BitbucketExporter(BaseExporter):
    """
    Bitbucket exporter that inherits from BaseExporter.
    
    This class provides functionality to export Bitbucket pull requests as Document objects,
    with support for authentication, repository filtering, and PR processing.
    
    Attributes:
        _bitbucket_client: Cached Bitbucket client instance
        _workspace_name: Bitbucket workspace name
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Bitbucket exporter.
        
        Args:
            config: Configuration dictionary containing:
                - workspace_name: Bitbucket workspace name (default: "omnidiandevelopmentteam")
                - max_retries: Maximum number of API retry attempts (default: 3)
                - retry_delay: Delay between retries in seconds (default: 2)
        """
        super().__init__(config)
        self._bitbucket_client = None
        self._workspace_name = self._get_config("workspace_name", "omnidiandevelopmentteam")
    
    def export(self, 
               repository: str = None, 
               state: str = "ALL", 
               days_ago: int = 30,
               project_key: str = None) -> Iterator[Dict[str, Any]]:
        """
        Export raw Bitbucket pull request data.
        
        Args:
            repository: Specific repository slug to export from (optional)
            state: PR state filter ("OPEN", "MERGED", "DECLINED", "ALL") (default: "ALL")
            days_ago: Number of days back to fetch PRs (default: 30)
            project_key: Specific project key to filter by (optional)
            
        Returns:
            Iterator of dictionaries containing raw Bitbucket PR data
            
        Yields:
            Dict containing:
                - pr_data: Raw PR data from Bitbucket API
                - workspace: Workspace name
                - project_key: Project key
                - repo_slug: Repository slug
                - comments: List of PR comments
                - commits: List of PR commits
        """
        client = self._get_bitbucket_client()
        workspace = client.workspaces.get(self._workspace_name)
        
        # Calculate earliest date for filtering
        earliest_date = None
        if days_ago > 0:
            earliest_date = datetime.now() - timedelta(days=days_ago)
            iso_date = earliest_date.isoformat()
            if 'Z' not in iso_date and '+' not in iso_date:
                iso_date += 'Z'
            query = f'updated_on >= "{iso_date}"'
        else:
            query = None
        
        self._log_info(f"Exporting PRs from workspace: {self._workspace_name}")
        if query:
            self._log_info(f"Filtering PRs updated since: {earliest_date}")
        
        pr_count = 0
        
        # Iterate over projects
        for project in workspace.projects.each():
            project_data = project.data
            current_project_key = project_data.get('key')
            
            # Filter by project if specified
            if project_key and current_project_key != project_key:
                continue
            
            self._log_info(f"Processing project: {current_project_key}")
            
            # Iterate over repositories in the project
            for repo in project.repositories.each():
                repo_data = repo.data
                repo_slug = repo_data.get('slug')
                
                # Filter by repository if specified
                if repository and repo_slug != repository:
                    continue
                
                self._log_info(f"Processing repository: {repo_slug}")
                
                try:
                    # Iterate over PRs with optional query filter
                    # Note: Bitbucket API uses different parameter names
                    pr_params = {}
                    if query:
                        pr_params['q'] = query
                    # Don't pass state parameter as it's not supported in the same way
                    
                    for pr in repo.pullrequests.each(**pr_params):
                        try:
                            pr_data = pr.data
                            
                            # Fetch comments
                            comments = []
                            try:
                                for comment in pr.comments():
                                    comments.append(comment.data)
                            except Exception as e:
                                self._log_warning(f"Error fetching comments for PR {pr_data.get('id')}: {e}")
                            
                            # Fetch commits
                            commits = []
                            try:
                                for commit in pr.commits:
                                    commits.append(commit.data)
                            except Exception as e:
                                self._log_warning(f"Error fetching commits for PR {pr_data.get('id')}: {e}")
                            
                            yield {
                                "pr_data": pr_data,
                                "workspace": self._workspace_name,
                                "project_key": current_project_key,
                                "repo_slug": repo_slug,
                                "comments": comments,
                                "commits": commits
                            }
                            
                            pr_count += 1
                            
                        except Exception as e:
                            self._log_error(f"Error processing PR in {repo_slug}: {e}")
                            continue
                            
                except Exception as e:
                    self._log_error(f"Error accessing PRs for repository {repo_slug}: {e}")
                    continue
        
        self._log_info(f"Exported {pr_count} pull requests")
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """
        Process raw Bitbucket data into Document objects.
        
        Args:
            raw_data: Iterator of raw Bitbucket PR data from export()
            
        Returns:
            Iterator of Document objects with processed Bitbucket metadata
            
        Yields:
            Document objects with Bitbucket PR-specific metadata and content
        """
        for item in raw_data:
            try:
                pr_data = item["pr_data"]
                workspace = item["workspace"]
                project_key = item["project_key"]
                repo_slug = item["repo_slug"]
                comments = item["comments"]
                commits = item["commits"]
                
                # Extract PR information
                pr_id = pr_data.get('id')
                pr_title = pr_data.get('title', '')
                pr_description = pr_data.get('description', '')
                state = pr_data.get('state', '')
                created_on = pr_data.get('created_on', '')
                updated_on = pr_data.get('updated_on', '')
                
                # Author information
                author_info = pr_data.get('author', {})
                author_name = author_info.get('display_name', 'Unknown')
                
                # Participants and reviewers
                participants = pr_data.get('participants', [])
                reviewers = ", ".join([
                    p.get('user', {}).get('display_name', 'Unknown') 
                    for p in participants 
                    if p.get('role') == 'REVIEWER'
                ])
                
                # Branch information
                source_branch = pr_data.get('source', {}).get('branch', {}).get('name', 'Unknown')
                destination_branch = pr_data.get('destination', {}).get('branch', {}).get('name', 'Unknown')
                
                # Process dates
                created_dt = self._iso_to_datetime(created_on) if created_on else None
                updated_dt = self._iso_to_datetime(updated_on) if updated_on else None
                
                # Process comments
                comments_text = ""
                if comments:
                    comments_text = "\n########## Comments ##########\n"
                    for comment in comments:
                        c_author = comment.get('user', {}).get('display_name', 'Unknown')
                        c_body = comment.get('content', {}).get('raw', '')
                        comments_text += f"{c_author}: {c_body}\n\n"
                
                # Process commits
                commit_authors_set = set()
                commit_text_list = []
                for commit in commits:
                    # Try user display_name first
                    c_author_name = commit.get('author', {}).get('user', {}).get('display_name')
                    if not c_author_name:
                        # Fallback to raw author if display_name is not available
                        c_author_name = commit.get('author', {}).get('raw', 'Unknown')
                    
                    commit_message = commit.get('message', '').strip()
                    commit_text_list.append(f"{c_author_name}: {commit_message}")
                    commit_authors_set.add(c_author_name)
                
                # Combine all participants
                all_participants_set = {author_name}  # Include PR author
                all_participants_set.update([
                    p['user']['display_name'] 
                    for p in participants 
                    if p.get('user', {}).get('display_name')
                ])
                all_participants_set.update(commit_authors_set)
                
                # Create content
                page_content = f"{pr_title}\n{pr_description}\n{comments_text}"
                if commit_text_list:
                    page_content += "\n########## Commits ##########\n"
                    page_content += "\n".join(commit_text_list)
                
                # Build metadata
                metadata = {
                    'id': str(pr_id),
                    'workspace': workspace,
                    'project_key': project_key,
                    'repo_slug': repo_slug,
                    'title': pr_title,
                    'author_name': author_name,
                    'state': state,
                    'reviewers': reviewers,
                    'source_branch': source_branch,
                    'destination_branch': destination_branch,
                    'all_participants': ", ".join(sorted(all_participants_set)),
                    'commit_authors': ", ".join(sorted(commit_authors_set)),
                    'source': 'bitbucket',
                    'type': 'bitbucket_pr',
                    'ingestion_timestamp': datetime.now().isoformat()
                }
                
                # Add timestamps
                if created_dt:
                    metadata['created_on'] = created_dt.isoformat()
                    metadata['created_ts'] = created_dt.timestamp()
                if updated_dt:
                    metadata['updated_on'] = updated_dt.isoformat()
                    metadata['updated_ts'] = updated_dt.timestamp()
                
                yield BitbucketPR(
                    id=str(pr_id),
                    page_content=page_content,
                    metadata=metadata
                )
                
            except Exception as e:
                self._log_error(f"Error processing Bitbucket PR: {e}")
                continue
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_bitbucket_client(self) -> Cloud:
        """
        Get authenticated Bitbucket client with retry logic.
        
        Returns:
            Authenticated Bitbucket client instance
        """
        if self._bitbucket_client is None:
            try:
                self._bitbucket_client = self._create_bitbucket_client()
                self._log_info("Successfully authenticated with Bitbucket API")
            except Exception as e:
                self._log_error(f"Failed to authenticate with Bitbucket: {e}")
                raise
        
        return self._bitbucket_client
    
    def _create_bitbucket_client(self) -> Cloud:
        """
        Create authenticated Bitbucket client.
        
        Returns:
            Authenticated Bitbucket client instance
        """
        try:
            # Try to get credentials from config first, then from Prefect Secret
            if self.config and all(k in self.config for k in ['username', 'password', 'url']):
                username = self.config['username']
                password = self.config['password']
                url = self.config['url']
            else:
                # Fallback to Prefect Secret
                secret_block = Secret.load("prefect-bitbucket-credentials")
                secret = secret_block.get()
                username = secret["username"]
                password = secret["app-password"]
                url = secret.get("url", "https://api.bitbucket.org")
            
            return Cloud(
                url=url,
                username=username,
                password=password
            )
            
        except Exception as e:
            self._log_error(f"Failed to create Bitbucket client: {e}")
            raise
    
    def _iso_to_datetime(self, iso_string: str) -> datetime:
        """
        Convert ISO datetime string to datetime object.
        
        Args:
            iso_string: ISO format datetime string
            
        Returns:
            datetime object
        """
        try:
            # Handle different ISO formats
            if iso_string.endswith('Z'):
                iso_string = iso_string[:-1] + '+00:00'
            return datetime.fromisoformat(iso_string)
        except ValueError:
            # Fallback for other formats
            return datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%S.%f%z')
    
    def get_repositories(self, project_key: str = None) -> List[Dict[str, str]]:
        """
        Get list of available repositories.
        
        Args:
            project_key: Optional project key to filter repositories
            
        Returns:
            List of dictionaries with repository information
        """
        client = self._get_bitbucket_client()
        workspace = client.workspaces.get(self._workspace_name)
        
        repositories = []
        
        for project in workspace.projects.each():
            project_data = project.data
            current_project_key = project_data.get('key')
            
            if project_key and current_project_key != project_key:
                continue
            
            for repo in project.repositories.each():
                repo_data = repo.data
                repositories.append({
                    'project_key': current_project_key,
                    'repo_slug': repo_data.get('slug'),
                    'repo_name': repo_data.get('name'),
                    'repo_full_name': repo_data.get('full_name')
                })
        
        return repositories
    
    def get_projects(self) -> List[Dict[str, str]]:
        """
        Get list of available projects.
        
        Returns:
            List of dictionaries with project information
        """
        client = self._get_bitbucket_client()
        workspace = client.workspaces.get(self._workspace_name)
        
        projects = []
        
        for project in workspace.projects.each():
            project_data = project.data
            projects.append({
                'key': project_data.get('key'),
                'name': project_data.get('name'),
                'description': project_data.get('description', '')
            })
        
        return projects