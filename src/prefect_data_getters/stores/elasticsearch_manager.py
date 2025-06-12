"""
Elasticsearch Manager for centralized document storage operations.
"""

from typing import List, Optional, Type, Dict, Any, Union
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError, ConnectionError
import logging
from prefect_data_getters.utilities.constants import ES_URL
from prefect_data_getters.stores.documents_new import AIDocument

logger = logging.getLogger(__name__)

class ElasticsearchManager:
    """
    Centralized Elasticsearch operations for AIDocuments.
    
    This class provides a high-level interface for storing, retrieving,
    and searching AIDocument instances in Elasticsearch.
    """
    
    def __init__(self, es_client: Optional[Elasticsearch] = None, max_retries: int = 3):
        """
        Initialize ElasticsearchManager.
        
        Args:
            es_client: Optional Elasticsearch client instance
            max_retries: Maximum number of retry attempts for failed operations
        """
        self.es = es_client or Elasticsearch(ES_URL)
        self.max_retries = max_retries
    
    def save_document(self, document: AIDocument, index_name: str) -> bool:
        """
        Save a single document to Elasticsearch.
        
        Args:
            document: AIDocument instance to save
            index_name: Name of the Elasticsearch index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_dict = document.to_dict()
            response = self.es.index(
                index=index_name,
                id=document.get_display_id(),
                body=doc_dict
            )
            logger.info(f"Saved document {document.get_display_id()} to index {index_name}")
            return response.get('result') in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"Error saving document {document.get_display_id()}: {e}")
            return False
    
    def save_documents(self, documents: List[AIDocument], index_name: str) -> Dict[str, int]:
        """
        Save multiple documents using bulk API.
        
        Args:
            documents: List of AIDocument instances to save
            index_name: Name of the Elasticsearch index
            
        Returns:
            Dictionary with success/failure counts
        """
        if not documents:
            return {'success': 0, 'failed': 0}
        
        actions = []
        for doc in documents:
            action = {
                "_op_type": "index",
                "_index": index_name,
                "_id": doc.get_display_id(),
                "_source": doc.to_dict()
            }
            actions.append(action)
        
        try:
            success_count, failed_items = helpers.bulk(
                self.es, 
                actions,
                max_retries=self.max_retries,
                initial_backoff=2,
                max_backoff=600
            )
            
            failed_count = len(failed_items) if failed_items else 0
            logger.info(f"Bulk save to {index_name}: {success_count} success, {failed_count} failed")
            
            return {'success': success_count, 'failed': failed_count}
            
        except Exception as e:
            logger.error(f"Error in bulk save to {index_name}: {e}")
            return {'success': 0, 'failed': len(documents)}
    
    def upsert_documents(self, documents: List[AIDocument], index_name: str) -> Dict[str, int]:
        """
        Upsert multiple documents using bulk API.
        
        Args:
            documents: List of AIDocument instances to upsert
            index_name: Name of the Elasticsearch index
            
        Returns:
            Dictionary with success/failure counts
        """
        if not documents:
            return {'success': 0, 'failed': 0}
        
        actions = []
        for doc in documents:
            action = {
                "_op_type": "update",
                "_index": index_name,
                "_id": doc.get_display_id(),
                "doc": doc.to_dict(),
                "doc_as_upsert": True
            }
            actions.append(action)
        
        try:
            success_count, failed_items = helpers.bulk(
                self.es,
                actions,
                max_retries=self.max_retries,
                initial_backoff=2,
                max_backoff=600
            )
            
            failed_count = len(failed_items) if failed_items else 0
            logger.info(f"Bulk upsert to {index_name}: {success_count} success, {failed_count} failed")
            
            return {'success': success_count, 'failed': failed_count}
            
        except Exception as e:
            logger.error(f"Error in bulk upsert to {index_name}: {e}")
            return {'success': 0, 'failed': len(documents)}
    
    def load_document(self, doc_id: str, index_name: str, 
                     document_class: Type[AIDocument] = AIDocument) -> Optional[AIDocument]:
        """
        Load a document by ID.
        
        Args:
            doc_id: Document ID to load
            index_name: Name of the Elasticsearch index
            document_class: AIDocument subclass to instantiate
            
        Returns:
            AIDocument instance or None if not found
        """
        try:
            response = self.es.get(index=index_name, id=doc_id)
            doc = document_class.from_dict(response['_source'])
            logger.debug(f"Loaded document {doc_id} from index {index_name}")
            return doc
            
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found in index {index_name}")
            return None
        except Exception as e:
            logger.error(f"Error loading document {doc_id}: {e}")
            return None
    
    def search_documents(self, query: dict, index_name: str,
                        document_class: Type[AIDocument] = AIDocument,
                        size: int = 10) -> List[AIDocument]:
        """
        Search documents and return as AIDocument instances.
        
        Args:
            query: Elasticsearch query DSL
            index_name: Name of the Elasticsearch index
            document_class: AIDocument subclass to instantiate
            size: Maximum number of results to return
            
        Returns:
            List of AIDocument instances with search scores
        """
        try:
            query['size'] = size
            response = self.es.search(index=index_name, body=query)
            
            documents = []
            for hit in response['hits']['hits']:
                doc = document_class.from_dict(hit['_source'])
                doc.search_score = hit['_score']
                documents.append(doc)
            
            logger.debug(f"Search in {index_name} returned {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error searching in {index_name}: {e}")
            return []
    
    def delete_document(self, doc_id: str, index_name: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID to delete
            index_name: Name of the Elasticsearch index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.es.delete(index=index_name, id=doc_id)
            logger.info(f"Deleted document {doc_id} from index {index_name}")
            return response.get('result') == 'deleted'
            
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found for deletion in index {index_name}")
            return False
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    def index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists.
        
        Args:
            index_name: Name of the Elasticsearch index
            
        Returns:
            True if index exists, False otherwise
        """
        try:
            return self.es.indices.exists(index=index_name)
        except Exception as e:
            logger.error(f"Error checking if index {index_name} exists: {e}")
            return False
    
    def create_index(self, index_name: str, mapping: Optional[dict] = None) -> bool:
        """
        Create an index with optional mapping.
        
        Args:
            index_name: Name of the Elasticsearch index
            mapping: Optional index mapping
            
        Returns:
            True if successful, False otherwise
        """
        try:
            body = {"mappings": mapping} if mapping else {}
            response = self.es.indices.create(index=index_name, body=body)
            logger.info(f"Created index {index_name}")
            return response.get('acknowledged', False)
            
        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Elasticsearch cluster.
        
        Returns:
            Dictionary with health information
        """
        try:
            health = self.es.cluster.health()
            return {
                'status': health.get('status', 'unknown'),
                'cluster_name': health.get('cluster_name', 'unknown'),
                'number_of_nodes': health.get('number_of_nodes', 0),
                'active_shards': health.get('active_shards', 0),
                'connection': 'healthy'
            }
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return {
                'status': 'red',
                'connection': 'failed',
                'error': str(e)
            }