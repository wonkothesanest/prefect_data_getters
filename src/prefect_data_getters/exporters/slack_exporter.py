"""
Slack exporter implementation using the BaseExporter architecture.

This module provides the SlackExporter class that inherits from BaseExporter,
implementing Slack-specific functionality for exporting Slack messages as documents.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from time import sleep
from typing import Iterator, Optional, Dict, Any, List
from collections import defaultdict
import glob
import requests

from langchain_core.documents import Document
from tenacity import retry, stop_after_attempt, wait_fixed

from .base import BaseExporter
from .slack.slacker_module import Slacker, Conversations

# Import SlackMessageDocument with fallback to regular Document
try:
    from prefect_data_getters.stores.document_types.slack_document import SlackMessageDocument
except ImportError:
    # Fallback to regular Document if SlackMessageDocument is not available
    SlackMessageDocument = Document


class SlackExporter(BaseExporter):
    """
    Slack exporter that inherits from BaseExporter.
    
    This class provides functionality to export Slack messages as Document objects,
    with support for authentication, channel filtering, and message processing.
    
    Attributes:
        _slack_client: Cached Slack client instance
        _user_mapping: Cached user ID to name mapping
        _channel_mapping: Cached channel ID to name mapping
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Slack exporter.
        
        Args:
            config: Configuration dictionary containing:
                - token: Slack API token (required)
                - page_size: Number of messages to fetch per API call (default: 1000)
                - rate_limit_delay: Delay between API calls in seconds (default: 1.3)
                - max_retries: Maximum number of retries for rate-limited requests (default: 3)
        """
        super().__init__(config)
        
        # Validate required configuration
        self._validate_config(['token'])
        
        # Set default configuration values
        self.config.setdefault("page_size", 1000)
        self.config.setdefault("rate_limit_delay", 1.3)
        self.config.setdefault("max_retries", 3)
        
        # Initialize cached instances
        self._slack_client = None
        self._user_mapping = None
        self._channel_mapping = None
    
    def export(self, channels: List[str] = None, days_ago: int = 7, limit: int = None) -> Iterator[Dict[str, Any]]:
        """
        Export raw Slack messages.
        
        Args:
            channels: List of channel names to export. If None, exports all accessible channels
            days_ago: Number of days back to search for messages (default: 7)
            limit: Maximum number of messages to return per channel. If None, returns all matching messages
            
        Returns:
            Iterator[Dict[str, Any]]: Iterator yielding raw Slack message data
            
        Raises:
            Exception: If authentication fails or API errors occur
        """
        self._log_export_start(channels=channels, days_ago=days_ago, limit=limit)
        
        try:
            # Get Slack client
            slack_client = self._get_slack_client()
            
            # Get channel mapping
            channel_mapping = self._get_channel_mapping(slack_client)
            
            # Calculate oldest timestamp
            oldest_timestamp = self._calculate_oldest_timestamp(days_ago)
            
            # Get channels to process
            channels_to_process = self._get_channels_to_process(
                slack_client, channels, channel_mapping
            )
            
            # Process each channel and yield raw messages
            for channel in channels_to_process:
                try:
                    channel_name = channel['name']
                    channel_id = channel['id']
                    
                    self.logger.info(f"Exporting channel: {channel_name}")
                    
                    # Fetch messages for this channel
                    messages = self._fetch_channel_messages(
                        slack_client, channel_id, oldest_timestamp, limit
                    )
                    
                    # Yield raw messages with channel context
                    for message in messages:
                        # Add channel context to raw message
                        message['_channel_name'] = channel_name
                        message['_channel_id'] = channel_id
                        yield message
                            
                except Exception as e:
                    self.logger.error(f"Error exporting channel {channel.get('name', 'unknown')}: {e}")
                    continue
            
        except Exception as e:
            self._handle_api_error(e, "Slack message export")
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """
        Process raw Slack messages into Document objects.
        
        Args:
            raw_data: Iterator of raw Slack message dictionaries
            
        Returns:
            Iterator[Document]: Iterator yielding Document objects
        """
        # Get Slack client for user mapping
        slack_client = self._get_slack_client()
        user_mapping = self._get_user_mapping(slack_client)
        
        document_count = 0
        
        for message_data in raw_data:
            try:
                # Extract channel name from message context
                channel_name = message_data.get('_channel_name', 'unknown')
                
                document = self._process_message(
                    message_data, user_mapping, channel_name
                )
                if document:  # Only yield if message has content
                    yield document
                    document_count += 1
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                continue
        
        self._log_export_complete(document_count)
    
    def _get_slack_client(self):
        """
        Get an authenticated Slack client instance.
        
        Returns:
            Slacker client instance
        """
        if self._slack_client is None:
            try:
                self._slack_client = Slacker(self.config['token'])
                # Test authentication
                self._test_authentication(self._slack_client)
            except Exception as e:
                self._handle_authentication_error(e)
        
        return self._slack_client
    
    def _test_authentication(self, slack_client):
        """
        Test Slack authentication.
        
        Args:
            slack_client: Slacker client instance
            
        Raises:
            Exception: If authentication test fails
        """
        try:
            test_auth = slack_client.auth.test().body
            team_name = test_auth['team']
            current_user = test_auth['user']
            self.logger.info(f"Successfully authenticated for team {team_name} and user {current_user}")
        except Exception as e:
            raise Exception(f"Slack authentication failed: {e}")
    
    def _calculate_oldest_timestamp(self, days_ago: int) -> float:
        """
        Calculate the oldest timestamp for message filtering.
        
        Args:
            days_ago: Number of days back to search
            
        Returns:
            Unix timestamp as float
        """
        oldest_date = datetime.utcnow() - timedelta(days=days_ago)
        return oldest_date.timestamp()
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_user_mapping(self, slack_client) -> Dict[str, str]:
        """
        Get a mapping from user IDs to user names with retry logic.
        
        Args:
            slack_client: Slacker client instance
            
        Returns:
            Dictionary mapping user IDs to real names
        """
        if self._user_mapping is None:
            try:
                users = []
                users_list = slack_client.users.list(limit=200).body
                users.extend(users_list['members'])
                
                while users_list.get('response_metadata', {}).get('next_cursor'):
                    cursor = users_list['response_metadata']['next_cursor']
                    sleep(self.config['rate_limit_delay'])
                    users_list = slack_client.users.list(limit=200, cursor=cursor).body
                    users.extend(users_list['members'])
                
                self._user_mapping = defaultdict(
                    lambda: "Unknown",
                    {user['id']: user['profile'].get('real_name', user.get('name', 'Unknown')) 
                     for user in users}
                )
                
                self.logger.info(f"Loaded {len(users)} users")
                
            except Exception as e:
                self.logger.error(f"Error fetching users: {e}")
                self._user_mapping = defaultdict(lambda: "Unknown")
        
        return self._user_mapping
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_channel_mapping(self, slack_client) -> Dict[str, str]:
        """
        Get a mapping from channel IDs to channel names with retry logic.
        
        Args:
            slack_client: Slacker client instance
            
        Returns:
            Dictionary mapping channel IDs to names
        """
        if self._channel_mapping is None:
            try:
                channels = []
                
                # Fetch public channels
                channels_list = slack_client.conversations.list(
                    limit=200, types=('public_channel')
                ).body
                channels.extend(channels_list['channels'])
                
                while channels_list.get('response_metadata', {}).get('next_cursor'):
                    cursor = channels_list['response_metadata']['next_cursor']
                    sleep(self.config['rate_limit_delay'])
                    channels_list = slack_client.conversations.list(
                        limit=200, types=('public_channel'), cursor=cursor
                    ).body
                    channels.extend(channels_list['channels'])
                
                # Fetch private channels and group DMs
                groups_list = slack_client.conversations.list(
                    limit=200, types=('private_channel', 'mpim')
                ).body
                channels.extend(groups_list['channels'])
                
                while groups_list.get('response_metadata', {}).get('next_cursor'):
                    cursor = groups_list['response_metadata']['next_cursor']
                    sleep(self.config['rate_limit_delay'])
                    groups_list = slack_client.conversations.list(
                        limit=200, types=('private_channel', 'mpim'), cursor=cursor
                    ).body
                    channels.extend(groups_list['channels'])
                
                self._channel_mapping = {
                    channel['id']: channel['name'] for channel in channels
                }
                
                self.logger.info(f"Loaded {len(channels)} channels")
                
            except Exception as e:
                self.logger.error(f"Error fetching channels: {e}")
                self._channel_mapping = {}
        
        return self._channel_mapping
    
    def _get_channels_to_process(self, slack_client, channel_names: List[str] = None, 
                                channel_mapping: Dict[str, str] = None) -> List[Dict]:
        """
        Get the list of channels to process.
        
        Args:
            slack_client: Slacker client instance
            channel_names: List of specific channel names to process
            channel_mapping: Channel ID to name mapping
            
        Returns:
            List of channel dictionaries
        """
        try:
            all_channels = []
            
            # Get all accessible channels
            channels_list = slack_client.conversations.list(
                limit=200, types=('public_channel', 'private_channel', 'mpim')
            ).body
            all_channels.extend(channels_list['channels'])
            
            while channels_list.get('response_metadata', {}).get('next_cursor'):
                cursor = channels_list['response_metadata']['next_cursor']
                sleep(self.config['rate_limit_delay'])
                channels_list = slack_client.conversations.list(
                    limit=200, types=('public_channel', 'private_channel', 'mpim'), 
                    cursor=cursor
                ).body
                all_channels.extend(channels_list['channels'])
            
            # Filter channels if specific names provided
            if channel_names:
                filtered_channels = [
                    channel for channel in all_channels 
                    if channel['name'] in channel_names
                ]
                return filtered_channels
            else:
                # Filter to only member channels and exclude archived
                return [
                    channel for channel in all_channels 
                    if channel.get('is_member', False) and not channel.get('is_archived', False)
                ]
                
        except Exception as e:
            self.logger.error(f"Error getting channels to process: {e}")
            return []
    
    def _fetch_channel_messages(self, slack_client, channel_id: str, 
                               oldest_timestamp: float, limit: int = None) -> List[Dict]:
        """
        Fetch all messages from a channel.
        
        Args:
            slack_client: Slacker client instance
            channel_id: Channel ID to fetch messages from
            oldest_timestamp: Oldest timestamp to fetch messages from
            limit: Maximum number of messages to fetch
            
        Returns:
            List of message dictionaries
        """
        messages = []
        last_timestamp = None
        page_size = self.config['page_size']
        
        try:
            while True:
                try:
                    response = slack_client.conversations.history(
                        channel=channel_id,
                        latest=last_timestamp,
                        oldest=oldest_timestamp,
                        limit=page_size
                    ).body
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        retry_in_seconds = int(e.response.headers.get("Retry-After", 60))
                        self.logger.warning(f"Rate limit hit. Retrying in {retry_in_seconds} seconds.")
                        sleep(retry_in_seconds + 1)
                        
                        response = slack_client.conversations.history(
                            channel=channel_id,
                            latest=last_timestamp,
                            oldest=oldest_timestamp,
                            limit=page_size
                        ).body
                    else:
                        raise
                
                if 'messages' in response:
                    batch_messages = response['messages']
                    messages.extend(batch_messages)
                    
                    # Fetch replies for threaded messages
                    for message in batch_messages:
                        if message.get('thread_ts'):
                            try:
                                replies = self._fetch_thread_replies(
                                    slack_client, channel_id, message['thread_ts'], oldest_timestamp
                                )
                                messages.extend(replies)
                            except Exception as e:
                                self.logger.error(f"Error fetching thread replies: {e}")
                                continue
                
                # Check for pagination
                if not response.get('has_more', False):
                    break
                
                if limit and len(messages) >= limit:
                    messages = messages[:limit]
                    break
                
                # Update timestamp for next page
                if messages:
                    last_timestamp = messages[-1]['ts']
                
                # Rate limiting
                sleep(self.config['rate_limit_delay'])
                
        except Exception as e:
            self.logger.error(f"Error fetching messages from channel {channel_id}: {e}")
        
        # Sort messages by timestamp
        messages.sort(key=lambda msg: float(msg.get('ts', 0)))
        return messages
    
    def _fetch_thread_replies(self, slack_client, channel_id: str, 
                             thread_ts: str, oldest_timestamp: float) -> List[Dict]:
        """
        Fetch replies for a threaded message.
        
        Args:
            slack_client: Slacker client instance
            channel_id: Channel ID
            thread_ts: Thread timestamp
            oldest_timestamp: Oldest timestamp to fetch
            
        Returns:
            List of reply message dictionaries
        """
        replies = []
        last_timestamp = None
        
        try:
            while True:
                try:
                    response = slack_client.conversations.replies(
                        channel=channel_id,
                        ts=thread_ts,
                        latest=last_timestamp,
                        oldest=oldest_timestamp,
                        limit=self.config['page_size']
                    ).body
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        retry_in_seconds = int(e.response.headers.get("Retry-After", 60))
                        self.logger.warning(f"Rate limit hit in thread replies. Retrying in {retry_in_seconds} seconds.")
                        sleep(retry_in_seconds + 1)
                        
                        response = slack_client.conversations.replies(
                            channel=channel_id,
                            ts=thread_ts,
                            latest=last_timestamp,
                            oldest=oldest_timestamp,
                            limit=self.config['page_size']
                        ).body
                    else:
                        raise
                
                if 'messages' in response:
                    batch_replies = response['messages']
                    replies.extend(batch_replies)
                
                if not response.get('has_more', False):
                    break
                
                if replies:
                    last_timestamp = replies[-1]['ts']
                
                sleep(self.config['rate_limit_delay'])
                
        except Exception as e:
            self.logger.error(f"Error fetching thread replies for {thread_ts}: {e}")
        
        # Remove the first message (original thread message) and sort
        if replies and replies[0].get('ts') == thread_ts:
            replies = replies[1:]
        
        replies.sort(key=lambda msg: float(msg.get('ts', 0)))
        return replies
    
    def _process_message(self, message: Dict, user_mapping: Dict[str, str], 
                        channel_name: str) -> Optional[Document]:
        """
        Process a Slack message into a Document object.
        
        Args:
            message: Slack message dictionary
            user_mapping: User ID to name mapping
            channel_name: Name of the channel
            
        Returns:
            Document object with message content and metadata, or None if no content
        """
        # Extract message text
        text = message.get('text', '')
        
        # Skip messages without text content
        if not text or len(text.strip()) == 0:
            return None
        
        # Replace user mentions with real names
        text = self._replace_user_mentions(text, user_mapping)
        
        # Extract metadata
        metadata = self._extract_message_metadata(message, user_mapping, channel_name)
        
        # Create unique document ID
        doc_id = f"{channel_name}_{message.get('ts', '')}"
        
        # Create SlackMessageDocument
        document = SlackMessageDocument(
            page_content=text,
            metadata=metadata
        )
        
        # Set the document ID
        if hasattr(document, 'id'):
            document.id = doc_id
        
        return document
    
    def _replace_user_mentions(self, text: str, user_mapping: Dict[str, str]) -> str:
        """
        Replace user mentions in text with real names.
        
        Args:
            text: Message text
            user_mapping: User ID to name mapping
            
        Returns:
            Text with user mentions replaced
        """
        if "<@" in text:
            for user_id, real_name in user_mapping.items():
                mention = f"<@{user_id}>"
                text = text.replace(mention, f"@{real_name}")
        return text
    
    def _extract_message_metadata(self, message: Dict, user_mapping: Dict[str, str], 
                                 channel_name: str) -> Dict[str, Any]:
        """
        Extract metadata from a Slack message.
        
        Args:
            message: Slack message dictionary
            user_mapping: User ID to name mapping
            channel_name: Name of the channel
            
        Returns:
            Dictionary of metadata
        """
        # Start with all message fields except text and blocks
        metadata = {
            key: value for key, value in message.items() 
            if key not in ['text', 'blocks']
        }
        
        # Calculate reaction count
        reaction_count = 0
        try:
            for reaction in metadata.get("reactions", []):
                reaction_count += reaction.get("count", 0)
        except (TypeError, AttributeError):
            pass
        
        # Add additional metadata
        metadata.update({
            "type": "slack",
            "user": user_mapping.get(message.get("user"), "Unknown"),
            "channel": channel_name,
            "reaction_count": reaction_count,
        })
        
        # Process timestamp fields
        timestamp_fields = ["ts", "latest_reply", "thread_ts"]
        for field in timestamp_fields:
            try:
                if field in metadata and metadata[field]:
                    timestamp_value = float(metadata[field])
                    metadata[field] = timestamp_value
                    metadata[f"{field}_datetime"] = datetime.fromtimestamp(timestamp_value).isoformat()
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Could not process timestamp field {field}: {e}")
        
        return metadata
    
    def reset_cached_data(self) -> None:
        """
        Reset all cached data (client, user mapping, channel mapping).
        
        This is useful when you want to refresh the data or switch to a different workspace.
        """
        self._slack_client = None
        self._user_mapping = None
        self._channel_mapping = None
        self.logger.info("Reset all cached Slack data")
    
    def get_channels(self) -> Dict[str, str]:
        """
        Get the current channel mapping.
        
        Returns:
            Dictionary mapping channel IDs to names
        """
        slack_client = self._get_slack_client()
        return self._get_channel_mapping(slack_client)
    
    def get_users(self) -> Dict[str, str]:
        """
        Get the current user mapping.
        
        Returns:
            Dictionary mapping user IDs to names
        """
        slack_client = self._get_slack_client()
        return self._get_user_mapping(slack_client)