"""
Slab exporter implementation using the BaseExporter architecture.

This module provides the SlabExporter class that inherits from BaseExporter,
implementing Slab-specific functionality for exporting Slab documents.
"""

import json
import os
import glob
from datetime import datetime
from typing import Iterator, Optional, Dict, Any, List

from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import TextSplitter
from tenacity import retry, stop_after_attempt, wait_fixed

from prefect_data_getters.exporters.base import BaseExporter
from prefect_data_getters.utilities import parse_date
from prefect_data_getters.stores.vectorstore import get_embeddings_and_vectordb


class SlabExporter(BaseExporter):
    """
    Slab exporter that inherits from BaseExporter.
    
    This class provides functionality to export Slab documents as Document objects,
    with support for processing markdown files and their associated metadata.
    
    Attributes:
        _users_cache: Cached user data from allUsers.json
        _topics_cache: Cached topic data from allTopics.json
        _semantic_chunker: Optional text splitter for chunking documents
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Slab exporter.
        
        Args:
            config: Configuration dictionary containing:
                - backup_dir: Directory containing Slab backup files
                - split_documents: Whether to split documents into chunks (default: True)
                - chunk_threshold: Semantic chunker threshold (default: 50)
                - max_chunks: Maximum number of chunks per document (default: 10)
        """
        super().__init__(config)
        self._users_cache: Optional[Dict[str, Any]] = None
        self._topics_cache: Optional[Dict[str, Any]] = None
        self._semantic_chunker: Optional[TextSplitter] = None
        
        # Initialize semantic chunker if splitting is enabled
        split_documents = self._get_config("split_documents", True)
        if split_documents:
            try:
                embeddings_model, _ = get_embeddings_and_vectordb("slab_docs")
                chunk_threshold = self._get_config("chunk_threshold", 50)
                max_chunks = self._get_config("max_chunks", 10)
                self._semantic_chunker = SemanticChunker(
                    embeddings=embeddings_model,
                    breakpoint_threshold_amount=chunk_threshold,
                    number_of_chunks=max_chunks
                )
            except Exception as e:
                self._log_warning(f"Failed to initialize semantic chunker: {e}")
                self._semantic_chunker = None
    
    def export(self, backup_dir: str, file_pattern: str = "*.md") -> Iterator[Dict[str, Any]]:
        """
        Export raw Slab document data from backup files.
        
        Args:
            backup_dir: Directory containing Slab backup files
            file_pattern: Glob pattern for document files (default: "*.md")
            
        Returns:
            Iterator of dictionaries containing raw Slab document data
            
        Yields:
            Dict containing:
                - doc_file: Path to the markdown file
                - meta_file: Path to the corresponding JSON metadata file
                - content: Raw document content
                - metadata: Raw metadata from JSON file
        """
        if not os.path.exists(backup_dir):
            raise FileNotFoundError(f"Backup directory not found: {backup_dir}")
        
        # Load users and topics data once
        self._load_users_and_topics(backup_dir)
        
        # Find all document files
        slab_files = glob.glob(os.path.join(backup_dir, file_pattern))
        self._log_info(f"Found {len(slab_files)} Slab files in {backup_dir}")
        
        for doc_file in slab_files:
            try:
                meta_file = doc_file.replace(".md", ".json")
                
                if not os.path.exists(meta_file):
                    self._log_warning(f"Metadata file not found for {doc_file}, skipping")
                    continue
                
                # Read document content
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Read metadata
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                yield {
                    "doc_file": doc_file,
                    "meta_file": meta_file,
                    "content": content,
                    "metadata": metadata
                }
                
            except Exception as e:
                self._log_error(f"Error processing file {doc_file}: {e}")
                continue
    
    def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
        """
        Process raw Slab data into Document objects.
        
        Args:
            raw_data: Iterator of raw Slab document data from export()
            
        Returns:
            Iterator of Document objects with processed Slab metadata
            
        Yields:
            Document objects with Slab-specific metadata and content
        """
        for item in raw_data:
            try:
                content = item["content"]
                raw_metadata = item["metadata"]
                
                # Extract metadata from the nested structure
                slab_meta = raw_metadata.get("data", {}).get("post", {})
                if not slab_meta:
                    self._log_warning(f"Invalid metadata structure in {item.get('meta_file', 'unknown')}")
                    continue
                
                # Process topics
                topics_list = self._process_topics(slab_meta.get("topics", []))
                
                # Build processed metadata
                processed_metadata = {
                    "document_id": slab_meta.get("id"),
                    "title": slab_meta.get("title", ""),
                    "owner": self._get_user_info(slab_meta.get("owner", {}).get("id")),
                    "contributors": self._get_contributors_info(slab_meta.get("contributors", [])),
                    "topics": " ## ".join(topics_list),
                    "updated_at": parse_date(slab_meta.get("updatedAt")),
                    "created_at": parse_date(slab_meta.get("insertedAt")),
                    "slab_type": slab_meta.get("__typename", ""),
                    "source": "slab",
                    "ingestion_timestamp": datetime.now().isoformat()
                }
                
                # Generate documents (chunked or whole)
                if self._semantic_chunker and content.strip():
                    # Create chunked documents
                    processed_metadata["type"] = "slab_chunk"
                    idx = 0
                    for chunk in self._semantic_chunker.split_text(content):
                        if chunk.strip():
                            chunk_id = f"{processed_metadata['document_id']}_{idx}"
                            chunk_metadata = processed_metadata.copy()
                            chunk_metadata["chunk_index"] = idx
                            chunk_metadata["parent_document_id"] = processed_metadata["document_id"]
                            
                            yield Slab(
                                id=chunk_id,
                                page_content=chunk,
                                metadata=chunk_metadata
                            )
                            idx += 1
                else:
                    # Create single document
                    processed_metadata["type"] = "slab_document"
                    yield Document(
                        id=processed_metadata["document_id"],
                        page_content=content,
                        metadata=processed_metadata
                    )
                    
            except Exception as e:
                self._log_error(f"Error processing Slab document: {e}")
                continue
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _load_users_and_topics(self, backup_dir: str) -> None:
        """
        Load users and topics data from backup directory.
        
        Args:
            backup_dir: Directory containing allUsers.json and allTopics.json
        """
        try:
            # Load users
            users_file = os.path.join(os.path.dirname(backup_dir), 'allUsers.json')
            if os.path.exists(users_file):
                with open(users_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                self._users_cache = {
                    user['id']: user 
                    for user in users_data.get('data', {}).get('session', {}).get('organization', {}).get('users', [])
                }
            else:
                self._log_warning(f"Users file not found: {users_file}")
                self._users_cache = {}
            
            # Load topics
            topics_file = os.path.join(os.path.dirname(backup_dir), 'allTopics.json')
            if os.path.exists(topics_file):
                with open(topics_file, 'r', encoding='utf-8') as f:
                    topics_data = json.load(f)
                self._topics_cache = {
                    topic['id']: topic 
                    for topic in topics_data.get('data', {}).get('session', {}).get('organization', {}).get('topics', [])
                }
            else:
                self._log_warning(f"Topics file not found: {topics_file}")
                self._topics_cache = {}
                
        except Exception as e:
            self._log_error(f"Error loading users and topics data: {e}")
            self._users_cache = {}
            self._topics_cache = {}
    
    def _get_user_info(self, user_id: str) -> str:
        """
        Get user information by ID.
        
        Args:
            user_id: User ID to look up
            
        Returns:
            Formatted user information string
        """
        if not user_id or not self._users_cache:
            return ""
        
        user = self._users_cache.get(user_id)
        if user:
            name = user.get("name", "")
            email = user.get("email", "")
            return f"{name} - {email}" if email else name
        return ""
    
    def _get_contributors_info(self, contributors: List[Dict[str, Any]]) -> str:
        """
        Get formatted contributors information.
        
        Args:
            contributors: List of contributor dictionaries
            
        Returns:
            Comma-separated string of contributor information
        """
        contributor_info = []
        for contributor in contributors:
            user_info = self._get_user_info(contributor.get("id"))
            if user_info:
                contributor_info.append(user_info)
        return ", ".join(contributor_info)
    
    def _process_topics(self, topics: List[Dict[str, Any]]) -> List[str]:
        """
        Process topics with their hierarchical structure.
        
        Args:
            topics: List of topic dictionaries
            
        Returns:
            List of formatted topic strings with hierarchy
        """
        topics_list = []
        for topic in topics:
            topic_id = topic.get("id")
            if not topic_id or not self._topics_cache:
                continue
                
            try:
                root_topic = self._topics_cache.get(topic_id)
                if root_topic:
                    root_name = root_topic.get("name", "")
                    ancestors = self._get_topic_ancestors(topic_id)
                    ancestor_names = [ancestor.get("name", "") for ancestor in ancestors if ancestor.get("name")]
                    ancestor_names.reverse()
                    
                    if ancestor_names:
                        topics_list.append(f"{' / '.join(ancestor_names)} / {root_name}")
                    else:
                        topics_list.append(root_name)
            except Exception as e:
                self._log_warning(f"Error processing topic {topic_id}: {e}")
                continue
        
        return topics_list
    
    def _get_topic_ancestors(self, topic_id: str) -> List[Dict[str, Any]]:
        """
        Get topic ancestors for hierarchical structure.
        
        Args:
            topic_id: Topic ID to get ancestors for
            
        Returns:
            List of ancestor topic dictionaries
        """
        ancestors = []
        if not self._topics_cache:
            return ancestors
            
        current_topic = self._topics_cache.get(topic_id)
        while current_topic and current_topic.get('parent'):
            parent_id = current_topic['parent']['id']
            parent_topic = self._topics_cache.get(parent_id)
            if parent_topic:
                ancestors.append(parent_topic)
                current_topic = parent_topic
            else:
                break
        
        return ancestors