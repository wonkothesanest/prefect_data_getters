"""
Gmail exporter implementation using the BaseExporter architecture.

This module provides the GmailExporter class that inherits from BaseExporter,
implementing Gmail-specific functionality for exporting email documents.
"""

import base64
import os
import pickle
from datetime import datetime, timedelta
from email import message_from_bytes
from typing import Iterator, Optional, Dict, Any, List

from langchain_core.documents import Document
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from tenacity import retry, stop_after_attempt, wait_fixed

from prefect_data_getters.exporters.base import BaseExporter
from prefect_data_getters.utilities import parse_date
from prefect_data_getters.utilities.similarity import calculate_similarity


class GmailExporter(BaseExporter):
    """
    Gmail exporter that inherits from BaseExporter.
    
    This class provides functionality to export Gmail messages as Document objects,
    with support for authentication, querying, and message processing.
    
    Attributes:
        SCOPES: Gmail API scopes required for access
        _service: Cached Gmail service instance
        _label_mapping: Cached label ID to name mapping
    """
    
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Gmail exporter.
        
        Args:
            config: Configuration dictionary containing:
                - token_path: Path to Gmail token pickle file (default: "secrets/gmail_token.pickle")
                - credentials_path: Path to Google app credentials JSON (default: "secrets/google_app_creds.json")
                - oauth_port: Port for OAuth flow (default: 8080)
        """
        super().__init__(config)
        
        # Set default configuration values
        self.config.setdefault("token_path", "secrets/gmail_token.pickle")
        self.config.setdefault("credentials_path", "secrets/google_app_creds.json")
        self.config.setdefault("oauth_port", 8080)
        
        # Initialize cached instances
        self._service = None
        self._label_mapping = None
    
    def export(self, days_ago: int = 7, query: str = None, max_results: int = None) -> Iterator[Dict[str, Any]]:
        """
        Export raw Gmail messages.
        
        Args:
            days_ago: Number of days back to search for messages (default: 7)
            query: Custom Gmail search query. If None, uses default query with days_ago
            max_results: Maximum number of messages to return. If None, returns all matching messages
            
        Returns:
            Iterator[Dict[str, Any]]: Iterator yielding raw Gmail message data
            
        Raises:
            Exception: If authentication fails or API errors occur
        """
        self._log_export_start(days_ago=days_ago, query=query, max_results=max_results)
        
        try:
            # Build the query if not provided
            if query is None:
                query = self._build_default_query(days_ago)
            
            # Get Gmail service
            service = self._get_gmail_service()
            
            # Fetch raw messages
            messages = self._fetch_messages(service, query, max_results)
            
            # Yield raw message data
            for message in messages:
                yield message
            
        except Exception as e:
            self._handle_api_error(e, "Gmail message export")
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """
        Process raw Gmail messages into Document objects.
        
        Args:
            raw_data: Iterator of raw Gmail message dictionaries
            
        Returns:
            Iterator[Document]: Iterator yielding Document objects
        """
        # Get Gmail service for label mapping
        service = self._get_gmail_service()
        label_mapping = self._get_label_mapping(service)
        
        document_count = 0
        
        for message_data in raw_data:
            try:
                document = self._process_message(message_data, label_mapping)
                yield document
                document_count += 1
            except Exception as e:
                self.logger.error(f"Error processing message {message_data.get('Message-ID', 'unknown')}: {e}")
                continue
        
        self._log_export_complete(document_count)
    
    def _authenticate(self):
        """
        Authenticate with the Gmail API using OAuth.
        
        Returns:
            Credentials object for Gmail API access
            
        Raises:
            FileNotFoundError: If credentials file is not found
            Exception: If authentication fails
        """
        creds = None
        token_path = self.config["token_path"]
        creds_path = self.config["credentials_path"]
        
        # Load saved credentials if they exist
        if os.path.exists(token_path):
            try:
                with open(token_path, "rb") as token:
                    creds = pickle.load(token)
            except Exception as e:
                self.logger.warning(f"Error loading saved credentials: {e}")
                creds = None
        
        # If there are no valid credentials available, let the user log in
        if not creds or not creds.valid:
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            except Exception as e:
                self.logger.warning(f"Error refreshing credentials: {e}")
                creds = None
            
            if creds is None:
                # If there are no (valid) credentials available, let the user log in
                self.logger.info("No valid credentials found. Starting OAuth flow.")
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(f"Credentials file not found: {creds_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, self.SCOPES)
                creds = flow.run_local_server(port=self.config["oauth_port"], access_type='offline')
            
            # Save the credentials for the next run
            try:
                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)
            except Exception as e:
                self.logger.warning(f"Error saving credentials: {e}")
        
        return creds
    
    def _get_gmail_service(self):
        """
        Get an authenticated Gmail service instance.
        
        Returns:
            Gmail service instance
        """
        if self._service is None:
            try:
                creds = self._authenticate()
                self._service = build('gmail', 'v1', credentials=creds)
            except Exception as e:
                self._handle_authentication_error(e)
        
        return self._service
    
    def _build_default_query(self, days_ago: int) -> str:
        """
        Build the default Gmail search query.
        
        Args:
            days_ago: Number of days back to search
            
        Returns:
            Gmail search query string
        """
        query_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y/%m/%d')
        bad_labels = ['useless', 'not-important', 'tools-calendar', 'tools-alarms', 'tools-bitbucket']
        bad_labels_query = ' AND '.join([f"NOT label:{label}" for label in bad_labels])
        query = f"after:{query_date} AND {bad_labels_query} AND NOT in:spam AND NOT in:trash"
        return query
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_message_list(self, service, query: str, next_page_token=None, max_results=None):
        """
        Get list of messages matching query with retry logic.
        
        Args:
            service: Gmail service instance
            query: Gmail search query
            next_page_token: Token for pagination
            max_results: Maximum results per page
            
        Returns:
            API response with message list
        """
        return service.users().messages().list(
            userId='me', 
            q=query, 
            pageToken=next_page_token, 
            maxResults=max_results
        ).execute()
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_message(self, service, msg_id: str):
        """
        Get full message content with retry logic.
        
        Args:
            service: Gmail service instance
            msg_id: Message ID
            
        Returns:
            Full message data
        """
        return service.users().messages().get(userId="me", id=msg_id, format='raw').execute()
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_labels(self, service):
        """
        Get Gmail labels with retry logic.
        
        Args:
            service: Gmail service instance
            
        Returns:
            Labels response
        """
        return service.users().labels().list(userId='me').execute()
    
    def _get_label_mapping(self, service):
        """
        Get a mapping from label IDs to label names.
        
        Args:
            service: Gmail service instance
            
        Returns:
            Dictionary mapping label IDs to names
        """
        if self._label_mapping is None:
            try:
                response = self._get_labels(service)
                labels = response.get('labels', [])
                self._label_mapping = {label['id']: label['name'] for label in labels}
            except Exception as e:
                self.logger.error(f"Error fetching labels: {e}")
                self._label_mapping = {}
        
        return self._label_mapping
    
    def _fetch_messages(self, service, query: str, max_results: int = None) -> List:
        """
        Fetch all messages matching the query.
        
        Args:
            service: Gmail service instance
            query: Gmail search query
            max_results: Maximum number of messages to fetch
            
        Returns:
            List of processed email message objects
        """
        messages = []
        next_page_token = None
        
        while True:
            try:
                response = self._get_message_list(service, query, next_page_token, max_results)
                
                if 'messages' in response:
                    messages.extend(response['messages'])
                
                next_page_token = response.get('nextPageToken')
                
                if not next_page_token or (max_results is not None and len(messages) >= max_results):
                    break
                    
            except Exception as e:
                self.logger.error(f"Error fetching message list: {e}")
                break
        
        # Fetch full message content
        full_messages = []
        for msg in messages:
            try:
                msg_id = msg['id']
                message = self._get_message(service, msg_id)
                msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
                mime_msg = message_from_bytes(msg_str)
                
                # Add Gmail-specific headers
                mime_msg.add_header("Google-ID", msg_id)
                mime_msg.add_header("Google-Thread-ID", msg['threadId'])
                
                full_messages.append(mime_msg)
                
            except Exception as e:
                self.logger.error(f"Error fetching message {msg_id}: {e}")
                continue
        
        return full_messages
    
    def _process_message(self, message, label_mapping: Dict[str, str]) -> Document:
        """
        Process a Gmail message into a Document object.
        
        Args:
            message: Email message object
            label_mapping: Mapping of label IDs to names
            
        Returns:
            Document object with message content and metadata
        """
        # Extract metadata
        metadata = self._extract_metadata(message)
        
        # Add label information
        if hasattr(message, 'get') and message.get('labelIds'):
            labels = [label_mapping.get(label_id, label_id) for label_id in message.get('labelIds', [])]
            metadata['labels'] = ','.join(labels)
        
        # Extract email body
        body = self._extract_email_body(message)
        
        # Create Document object
        document = Document(
            id=metadata.get('google-id'),
            page_content=body,
            metadata=metadata
        )
        
        return document
    
    def _extract_metadata(self, message) -> Dict[str, Any]:
        """
        Extract metadata from the Gmail message.
        
        Args:
            message: Email message object
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        headers = [
            'Message-ID', 'From', 'To', 'Cc', 'Bcc', 'Subject', 'Date', 
            'Reply-To', 'In-Reply-To', 'References', 'Google-ID', 'Google-Thread-ID'
        ]
        
        for header in headers:
            value = message.get(header)
            if value:
                stripped_value = str(value).strip()
                if header == 'Date':
                    try:
                        metadata[header.lower()] = parse_date(stripped_value)
                    except Exception as e:
                        self.logger.warning(f"Error parsing date '{stripped_value}': {e}")
                        metadata[header.lower()] = stripped_value
                else:
                    metadata[header.lower()] = stripped_value
        
        return metadata
    
    def _extract_email_body(self, message) -> str:
        """
        Extract the body from an email message.
        
        Args:
            message: Email message object
            
        Returns:
            Email body text
        """
        if message.is_multipart():
            parts = []
            for part in message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                # Skip attachments
                if content_disposition and 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    charset = part.get_content_charset()
                    payload = part.get_payload(decode=True)
                    if payload:
                        try:
                            parts.append(payload.decode(charset or 'utf-8', errors='replace'))
                        except Exception as e:
                            self.logger.warning(f"Error decoding email part: {e}")
                            continue
            
            return '\n'.join(parts)
        else:
            payload = message.get_payload(decode=True)
            charset = message.get_content_charset()
            if payload:
                try:
                    return payload.decode(charset or 'utf-8', errors='replace')
                except Exception as e:
                    self.logger.warning(f"Error decoding email payload: {e}")
                    return str(payload)
        
        return ''
    
    def apply_labels_to_email(self, email_id: str, 
                             category_labels: List[str] = [], 
                             team_labels: List[str] = [],  
                             project_labels: List[str] = [],  
                             systems_labels: List[str] = []) -> None:
        """
        Apply suggested labels to the processed email.
        
        Args:
            email_id: Gmail message ID
            category_labels: List of category labels to apply
            team_labels: List of team labels to apply
            project_labels: List of project labels to apply
            systems_labels: List of system labels to apply
        """
        try:
            service = self._get_gmail_service()
            created_labels = []
            existing_labels_to_apply = []
            
            all_label_groups = {
                "Cats": category_labels, 
                "Teams": team_labels, 
                "Projects": project_labels, 
                "Systems": systems_labels
            }
            
            existing_labels = self._get_label_mapping(service)
            
            for label_type, label_list in all_label_groups.items():
                # Smoosh similar labels together
                smooshed_labels = self._smoosh_labels_together(
                    label_list, label_type, existing_labels
                )
                
                for label in smooshed_labels:
                    label_name = f'AI/{label_type}/{label}'
                    
                    # Check if label exists
                    existing_label_id = None
                    for label_id, name in existing_labels.items():
                        if name == label_name:
                            existing_label_id = label_id
                            break
                    
                    if existing_label_id:
                        existing_labels_to_apply.append(existing_label_id)
                    else:
                        # Create new label
                        try:
                            new_label = service.users().labels().create(
                                userId='me', 
                                body={'name': label_name}
                            ).execute()
                            created_labels.append(new_label['id'])
                            # Reset cached labels
                            self._label_mapping = None
                        except Exception as e:
                            self.logger.error(f"Error creating label '{label_name}': {e}")
                            continue
            
            # Apply labels to the email
            label_ids = existing_labels_to_apply + created_labels
            
            if label_ids:
                service.users().messages().modify(
                    userId='me', 
                    id=email_id, 
                    body={'addLabelIds': label_ids}
                ).execute()
                self.logger.info(f"Applied {len(label_ids)} labels to email {email_id}")
            
        except Exception as e:
            self._handle_api_error(e, f"applying labels to email {email_id}")
    
    def _smoosh_labels_together(self, suggested_labels: List[str], 
                               label_type: str, 
                               existing_labels: Dict[str, str], 
                               threshold: float = 0.60) -> List[str]:
        """
        Update labels based on similarity scores to avoid duplicates.
        
        Args:
            suggested_labels: List of suggested label names
            label_type: Type of labels (Cats, Teams, Projects, Systems)
            existing_labels: Dictionary of existing label IDs to names
            threshold: Similarity threshold for label matching
            
        Returns:
            List of updated label names
        """
        if not suggested_labels:
            return []
        
        # Get existing labels of this type
        existing_label_strings = [
            label.replace(f"AI/{label_type}/", "") 
            for label in existing_labels.values() 
            if label.startswith(f"AI/{label_type}/")
        ]
        
        if not existing_label_strings:
            return suggested_labels
        
        updated_labels = []
        
        for label in suggested_labels:
            try:
                similarities = calculate_similarity(existing_label_strings, label)
                
                # Find the most similar existing label above threshold
                best_match = None
                best_score = 0
                
                for result in similarities:
                    if result['similarity_score'] > threshold and result['similarity_score'] > best_score:
                        best_match = result['value']
                        best_score = result['similarity_score']
                
                if best_match:
                    updated_labels.append(best_match)
                else:
                    updated_labels.append(label)
                    
            except Exception as e:
                self.logger.warning(f"Error calculating similarity for label '{label}': {e}")
                updated_labels.append(label)
        
        return updated_labels
    
    def get_labels(self) -> Dict[str, str]:
        """
        Get all Gmail labels.
        
        Returns:
            Dictionary mapping label IDs to names
        """
        service = self._get_gmail_service()
        return self._get_label_mapping(service)
    
    def reset_cached_data(self) -> None:
        """
        Reset cached service and label data.
        Useful for testing or when credentials change.
        """
        self._service = None
        self._label_mapping = None