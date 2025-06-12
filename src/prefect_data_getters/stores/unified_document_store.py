"""
Unified Document Store - Single interface for all document operations.
"""

from typing import List, Optional, Dict, Any, Union
from prefect_data_getters.stores.elasticsearch_manager import ElasticsearchManager
from prefect_data_getters.stores.vectorstore import ESVectorStore
from prefect_data_getters.stores.document_registry import DocumentTypeRegistry
from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.utilities.constants import VECTOR_STORE_NAMES
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)

class UnifiedDocumentStore:
    """
    Single interface for all document operations.
    
    This class coordinates between Elasticsearch (for full-text search and storage)
    and vector stores (for semantic search) while providing a unified API.
    """
    
    def __init__(self, es_manager: Optional[ElasticsearchManager] = None):
        """
        Initialize UnifiedDocumentStore.
        
        Args:
            es_manager: Optional ElasticsearchManager instance
        """
        self.es_manager = es_manager or ElasticsearchManager()
        self.vector_stores: Dict[str, ESVectorStore] = {}
        self.registry = DocumentTypeRegistry()
    
    def get_vector_store(self, store_name: VECTOR_STORE_NAMES) -> ESVectorStore:
        """
        Get or create vector store for given name.
        
        Args:
            store_name: Name of the vector store
            
        Returns:
            ESVectorStore instance
        """
        if store_name not in self.vector_stores:
            self.vector_stores[store_name] = ESVectorStore(store_name)
        return self.vector_stores[store_name]
    
    def store_documents(self, documents: List[AIDocument], store_name: VECTOR_STORE_NAMES,
                       store_in_vector: bool = True, store_in_elasticsearch: bool = True) -> Dict[str, Any]:
        """
        Store documents in both Elasticsearch and vector store.
        
        Args:
            documents: List of AIDocument instances to store
            store_name: Name of the store/index
            store_in_vector: Whether to store in vector store
            store_in_elasticsearch: Whether to store in Elasticsearch
            
        Returns:
            Dictionary with operation results
        """
        results = {
            'elasticsearch': {'success': 0, 'failed': 0},
            'vector_store': {'success': 0, 'failed': 0},
            'total_documents': len(documents)
        }
        
        if not documents:
            return results
        
        # Store in Elasticsearch for full-text search and primary storage
        if store_in_elasticsearch:
            try:
                es_result = self.es_manager.upsert_documents(documents, store_name)
                results['elasticsearch'] = es_result
                logger.info(f"Elasticsearch storage: {es_result}")
            except Exception as e:
                logger.error(f"Error storing in Elasticsearch: {e}")
                results['elasticsearch']['failed'] = len(documents)
        
        # Store in vector store for semantic search
        if store_in_vector:
            try:
                vector_store = self.get_vector_store(store_name)
                # Convert AIDocuments to base Documents for vector storage
                base_docs = [Document(
                    page_content=doc.page_content, 
                    metadata=doc.metadata,
                    id=doc.get_display_id()
                ) for doc in documents]
                
                vector_store.batch_process_and_store(base_docs)
                results['vector_store']['success'] = len(documents)
                logger.info(f"Vector store storage: {len(documents)} documents")
            except Exception as e:
                logger.error(f"Error storing in vector store: {e}")
                results['vector_store']['failed'] = len(documents)
        
        return results
    
    def search_documents(self, 
                        query: str, 
                        store_names: List[VECTOR_STORE_NAMES],
                        search_type: str = "hybrid",
                        top_k: int = 10,
                        filters: Optional[Dict[str, Any]] = None,
                        **kwargs) -> List[AIDocument]:
        """
        Unified search across multiple stores.
        
        Args:
            query: Search query string
            store_names: List of store names to search
            search_type: Type of search ("text", "vector", "hybrid")
            top_k: Maximum number of results to return
            filters: Optional filters to apply
            **kwargs: Additional search parameters
            
        Returns:
            List of AIDocument instances with search scores
        """
        all_results = []
        
        for store_name in store_names:
            document_class = self.registry.get_document_class(store_name)
            
            if search_type in ["text", "hybrid"]:
                # Elasticsearch full-text search
                es_query = self._build_elasticsearch_query(query, filters, top_k)
                es_results = self.es_manager.search_documents(
                    es_query, store_name, document_class, top_k
                )
                all_results.extend(es_results)
            
            if search_type in ["vector", "hybrid"]:
                # Vector similarity search
                try:
                    vector_store = self.get_vector_store(store_name)
                    vector_results = vector_store.getESStore().similarity_search(query, k=top_k)
                    
                    # Convert back to AIDocuments
                    ai_docs = []
                    for doc in vector_results:
                        ai_doc = document_class.from_dict({
                            'page_content': doc.page_content,
                            'metadata': doc.metadata or {},
                            'id': doc.metadata.get('id') if doc.metadata else None
                        })
                        ai_doc.search_score = getattr(doc, 'search_score', 0.0)
                        ai_docs.append(ai_doc)
                    
                    all_results.extend(ai_docs)
                except Exception as e:
                    logger.error(f"Error in vector search for {store_name}: {e}")
        
        # Remove duplicates and sort by score
        unique_results = self._deduplicate_results(all_results)
        return sorted(unique_results, key=lambda x: x.search_score or 0, reverse=True)[:top_k]
    
    def load_document(self, doc_id: str, store_name: VECTOR_STORE_NAMES) -> Optional[AIDocument]:
        """
        Load a document by ID from Elasticsearch.
        
        Args:
            doc_id: Document ID to load
            store_name: Name of the store/index
            
        Returns:
            AIDocument instance or None if not found
        """
        document_class = self.registry.get_document_class(store_name)
        return self.es_manager.load_document(doc_id, store_name, document_class)
    
    def delete_document(self, doc_id: str, store_name: VECTOR_STORE_NAMES) -> bool:
        """
        Delete a document from both Elasticsearch and vector store.
        
        Args:
            doc_id: Document ID to delete
            store_name: Name of the store/index
            
        Returns:
            True if successful in at least one store
        """
        es_success = self.es_manager.delete_document(doc_id, store_name)
        
        # Note: Vector store deletion would require additional implementation
        # as current ESVectorStore doesn't support deletion by ID
        
        return es_success
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all storage backends.
        
        Returns:
            Dictionary with health information for all backends
        """
        return {
            'elasticsearch': self.es_manager.health_check(),
            'vector_stores': {name: 'not_implemented' for name in self.vector_stores.keys()},
            'registry': {
                'registered_types': len(self.registry.list_registered_types()),
                'types': list(self.registry.list_registered_types().keys())
            }
        }
    
    def _build_elasticsearch_query(self, query: str, filters: Optional[Dict[str, Any]], 
                                  size: int) -> Dict[str, Any]:
        """
        Build Elasticsearch query from parameters.
        
        Args:
            query: Search query string
            filters: Optional filters to apply
            size: Maximum number of results
            
        Returns:
            Elasticsearch query dictionary
        """
        es_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["page_content^2", "metadata.*"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "size": size,
            "highlight": {
                "fields": {
                    "page_content": {"fragment_size": 150, "number_of_fragments": 3}
                }
            }
        }
        
        # Add filters if provided
        if filters:
            bool_query = {
                "bool": {
                    "must": [es_query["query"]],
                    "filter": []
                }
            }
            
            for field, value in filters.items():
                bool_query["bool"]["filter"].append({
                    "term": {f"metadata.{field}": value}
                })
            
            es_query["query"] = bool_query
        
        return es_query
    
    def _deduplicate_results(self, results: List[AIDocument]) -> List[AIDocument]:
        """
        Remove duplicate documents based on display ID.
        
        Args:
            results: List of AIDocument instances
            
        Returns:
            List of unique AIDocument instances
        """
        seen_ids = set()
        unique_results = []
        
        for doc in results:
            doc_id = doc.get_display_id()
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(doc)
        
        return unique_results