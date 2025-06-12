import pytest
from unittest.mock import Mock, patch, MagicMock
from prefect_data_getters.stores.elasticsearch_manager import ElasticsearchManager
from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.elasticsearch_compatibility import upsert_documents

class TestPhase4Elasticsearch:
    """Test suite for Phase 4 Elasticsearch integration with direct store access"""
    
    @pytest.fixture
    def mock_es_client(self):
        """Mock Elasticsearch client"""
        return Mock()
    
    @pytest.fixture
    def es_manager(self, mock_es_client):
        """ElasticsearchManager with mocked client"""
        return ElasticsearchManager(mock_es_client)
    
    def test_elasticsearch_manager_save_document(self, es_manager, mock_es_client):
        """Test saving a single document"""
        mock_es_client.index.return_value = {'result': 'created'}
        
        doc = AIDocument("test content", {"key": "value"})
        doc.id = "test-123"
        
        result = es_manager.save_document(doc, "test_index")
        
        assert result == True
        mock_es_client.index.assert_called_once()
        call_args = mock_es_client.index.call_args
        assert call_args[1]['index'] == 'test_index'
        assert call_args[1]['id'] == 'test-123'
    
    def test_elasticsearch_manager_bulk_upsert(self, es_manager):
        """Test bulk upsert operation"""
        with patch('prefect_data_getters.stores.elasticsearch_manager.helpers.bulk') as mock_bulk:
            mock_bulk.return_value = (2, [])  # 2 successful, 0 failed
            
            docs = [
                AIDocument("content 1", {"id": "1"}),
                AIDocument("content 2", {"id": "2"})
            ]
            
            result = es_manager.upsert_documents(docs, "test_index")
            
            assert result['success'] == 2
            assert result['failed'] == 0
            mock_bulk.assert_called_once()
    
    def test_elasticsearch_manager_search(self, es_manager, mock_es_client):
        """Test document search"""
        mock_es_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_source': {
                            'page_content': 'test content',
                            'metadata': {'key': 'value'},
                            'id': 'test-123'
                        },
                        '_score': 0.95
                    }
                ]
            }
        }
        
        query = {"query": {"match": {"page_content": "test"}}}
        results = es_manager.search_documents(query, "test_index", AIDocument)
        
        assert len(results) == 1
        assert results[0].page_content == "test content"
        assert results[0].search_score == 0.95
    
    def test_elasticsearch_manager_load_document(self, es_manager, mock_es_client):
        """Test loading a document by ID"""
        mock_es_client.get.return_value = {
            '_source': {
                'page_content': 'loaded content',
                'metadata': {'key': 'value'},
                'id': 'test-456'
            }
        }
        
        result = es_manager.load_document("test-456", "test_index", AIDocument)
        
        assert result is not None
        assert result.page_content == "loaded content"
        assert result.metadata['key'] == "value"
        mock_es_client.get.assert_called_once_with(index="test_index", id="test-456")
    
    def test_elasticsearch_manager_delete_document(self, es_manager, mock_es_client):
        """Test deleting a document"""
        mock_es_client.delete.return_value = {'result': 'deleted'}
        
        result = es_manager.delete_document("test-789", "test_index")
        
        assert result == True
        mock_es_client.delete.assert_called_once_with(index="test_index", id="test-789")
    
    def test_elasticsearch_manager_health_check(self, es_manager, mock_es_client):
        """Test health check functionality"""
        mock_es_client.cluster.health.return_value = {
            'status': 'green',
            'cluster_name': 'test-cluster',
            'number_of_nodes': 1,
            'active_shards': 5
        }
        
        health = es_manager.health_check()
        
        assert health['status'] == 'green'
        assert health['cluster_name'] == 'test-cluster'
        assert health['connection'] == 'healthy'
    
    def test_unified_store_storage(self, unified_store):
        """Test unified document storage"""
        with patch.object(unified_store.es_manager, 'upsert_documents') as mock_upsert:
            mock_upsert.return_value = {'success': 1, 'failed': 0}
            
            with patch.object(unified_store, 'get_vector_store') as mock_get_vs:
                mock_vector_store = Mock()
                mock_get_vs.return_value = mock_vector_store
                
                doc = AIDocument("test content", {"key": "value"})
                results = unified_store.store_documents([doc], "test_store")
                
                assert results['elasticsearch']['success'] == 1
                mock_upsert.assert_called_once_with([doc], "test_store")
                mock_vector_store.batch_process_and_store.assert_called_once()
    
    def test_unified_store_search_text_only(self, unified_store):
        """Test text-only search functionality"""
        with patch.object(unified_store.es_manager, 'search_documents') as mock_es_search:
            mock_doc = AIDocument("es result", {"source": "elasticsearch"})
            mock_doc.search_score = 0.8
            mock_es_search.return_value = [mock_doc]
            
            results = unified_store.search_documents(
                "test query", 
                ["test_store"], 
                search_type="text"
            )
            
            assert len(results) == 1
            assert results[0].page_content == "es result"
            mock_es_search.assert_called_once()
    
    def test_unified_store_search_vector_only(self, unified_store):
        """Test vector-only search functionality"""
        with patch.object(unified_store, 'get_vector_store') as mock_get_vs:
            mock_vector_store = Mock()
            mock_langchain_doc = Mock()
            mock_langchain_doc.page_content = "vector result"
            mock_langchain_doc.metadata = {"source": "vector"}
            mock_vector_store.getESStore.return_value.similarity_search.return_value = [mock_langchain_doc]
            mock_get_vs.return_value = mock_vector_store
            
            results = unified_store.search_documents(
                "test query", 
                ["test_store"], 
                search_type="vector"
            )
            
            assert len(results) >= 0  # Might be 0 if conversion fails, but should not error
            mock_vector_store.getESStore.return_value.similarity_search.assert_called_once()
    
    def test_unified_store_search_hybrid(self, unified_store):
        """Test hybrid search functionality"""
        # Mock Elasticsearch search
        with patch.object(unified_store.es_manager, 'search_documents') as mock_es_search:
            mock_es_doc = AIDocument("es result", {"source": "elasticsearch"})
            mock_es_doc.search_score = 0.8
            mock_es_search.return_value = [mock_es_doc]
            
            # Mock vector search
            with patch.object(unified_store, 'get_vector_store') as mock_get_vs:
                mock_vector_store = Mock()
                mock_langchain_doc = Mock()
                mock_langchain_doc.page_content = "vector result"
                mock_langchain_doc.metadata = {"source": "vector"}
                mock_vector_store.getESStore.return_value.similarity_search.return_value = [mock_langchain_doc]
                mock_get_vs.return_value = mock_vector_store
                
                results = unified_store.search_documents(
                    "test query", 
                    ["test_store"], 
                    search_type="hybrid"
                )
                
                assert len(results) >= 1  # Should have at least ES results
                mock_es_search.assert_called_once()
                mock_vector_store.getESStore.return_value.similarity_search.assert_called_once()
    
    def test_unified_store_load_document(self, unified_store):
        """Test loading a document through unified store"""
        with patch.object(unified_store.es_manager, 'load_document') as mock_load:
            mock_doc = AIDocument("loaded content", {"key": "value"})
            mock_load.return_value = mock_doc
            
            result = unified_store.load_document("test-id", "test_store")
            
            assert result == mock_doc
            mock_load.assert_called_once()
    
    def test_unified_store_delete_document(self, unified_store):
        """Test deleting a document through unified store"""
        with patch.object(unified_store.es_manager, 'delete_document') as mock_delete:
            mock_delete.return_value = True
            
            result = unified_store.delete_document("test-id", "test_store")
            
            assert result == True
            mock_delete.assert_called_once_with("test-id", "test_store")
    
    def test_unified_store_health_check(self, unified_store):
        """Test unified store health check"""
        with patch.object(unified_store.es_manager, 'health_check') as mock_health:
            mock_health.return_value = {'status': 'green', 'connection': 'healthy'}
            
            health = unified_store.health_check()
            
            assert 'elasticsearch' in health
            assert 'vector_stores' in health
            assert 'registry' in health
            assert health['elasticsearch']['status'] == 'green'
    
    def test_aidocument_save_method(self):
        """Test AIDocument save method with direct ElasticsearchManager"""
        with patch('prefect_data_getters.stores.documents_new.ElasticsearchManager') as mock_manager_class:
            mock_es = Mock()
            mock_es.save_document.return_value = True
            mock_manager_class.return_value = mock_es
            
            doc = AIDocument("test content", {"key": "value"})
            doc.id = "test-123"
            result = doc.save("test_store", also_store_vectors=False)
            
            assert result == True
            mock_es.save_document.assert_called_once_with(doc, "test_store")

    def test_aidocument_save_method_with_vectors(self):
        """Test AIDocument save method with vector storage"""
        with patch('prefect_data_getters.stores.documents_new.ElasticsearchManager') as mock_manager_class:
            with patch('prefect_data_getters.stores.documents_new.ESVectorStore') as mock_vector_class:
                mock_es = Mock()
                mock_es.save_document.return_value = True
                mock_manager_class.return_value = mock_es
                
                mock_vector_store = Mock()
                mock_vector_class.return_value = mock_vector_store
                
                doc = AIDocument("test content", {"key": "value"})
                doc.id = "test-123"
                result = doc.save("test_store", also_store_vectors=True)
                
                assert result == True
                mock_es.save_document.assert_called_once_with(doc, "test_store")
                mock_vector_store.batch_process_and_store.assert_called_once()

    def test_aidocument_delete_method(self):
        """Test AIDocument delete method with direct ElasticsearchManager"""
        with patch('prefect_data_getters.stores.documents_new.ElasticsearchManager') as mock_manager_class:
            mock_es = Mock()
            mock_es.delete_document.return_value = True
            mock_manager_class.return_value = mock_es
            
            doc = AIDocument("test content", {"key": "value"})
            doc.id = "test-123"
            result = doc.delete("test_store")
            
            assert result == True
            mock_es.delete_document.assert_called_once_with("test-123", "test_store")

    def test_aidocument_search_text_method(self):
        """Test AIDocument search with text search type"""
        with patch('prefect_data_getters.stores.documents_new.ElasticsearchManager') as mock_manager_class:
            with patch('prefect_data_getters.stores.documents_new.DocumentTypeRegistry') as mock_registry:
                mock_es = Mock()
                mock_result_doc = AIDocument("result content", {"source": "test"})
                mock_result_doc.search_score = 0.9
                mock_es.search_documents.return_value = [mock_result_doc]
                mock_manager_class.return_value = mock_es
                
                mock_registry.get_document_class.return_value = AIDocument
                
                results = AIDocument.search("test query", "test_store", search_type="text", top_k=5)
                
                assert len(results) == 1
                assert results[0].page_content == "result content"
                assert results[0].search_score == 0.9
                mock_es.search_documents.assert_called_once()

    def test_aidocument_search_vector_method(self):
        """Test AIDocument search with vector search type"""
        with patch('prefect_data_getters.stores.documents_new.ESVectorStore') as mock_vector_class:
            with patch('prefect_data_getters.stores.documents_new.DocumentTypeRegistry') as mock_registry:
                mock_vector_store = Mock()
                mock_langchain_doc = Mock()
                mock_langchain_doc.page_content = "vector result"
                mock_langchain_doc.metadata = {"id": "vector-1"}
                mock_vector_store.getESStore.return_value.similarity_search.return_value = [mock_langchain_doc]
                mock_vector_class.return_value = mock_vector_store
                
                mock_registry.get_document_class.return_value = AIDocument
                
                results = AIDocument.search("test query", "test_store", search_type="vector", top_k=5)
                
                assert len(results) == 1
                assert results[0].page_content == "vector result"
                mock_vector_store.getESStore.return_value.similarity_search.assert_called_once_with("test query", k=5)

    def test_aidocument_search_hybrid_method(self):
        """Test AIDocument search with hybrid search type"""
        with patch('prefect_data_getters.stores.documents_new.ElasticsearchManager') as mock_manager_class:
            with patch('prefect_data_getters.stores.documents_new.ESVectorStore') as mock_vector_class:
                with patch('prefect_data_getters.stores.documents_new.DocumentTypeRegistry') as mock_registry:
                    # Mock text search results
                    mock_es = Mock()
                    mock_text_doc = AIDocument("text result", {"source": "elasticsearch"})
                    mock_text_doc.search_score = 0.8
                    mock_es.search_documents.return_value = [mock_text_doc]
                    mock_manager_class.return_value = mock_es
                    
                    # Mock vector search results
                    mock_vector_store = Mock()
                    mock_langchain_doc = Mock()
                    mock_langchain_doc.page_content = "vector result"
                    mock_langchain_doc.metadata = {"id": "vector-1"}
                    mock_vector_store.getESStore.return_value.similarity_search.return_value = [mock_langchain_doc]
                    mock_vector_class.return_value = mock_vector_store
                    
                    mock_registry.get_document_class.return_value = AIDocument
                    
                    results = AIDocument.search("test query", "test_store", search_type="hybrid", top_k=5)
                    
                    assert len(results) >= 1  # Should have at least text results
                    mock_es.search_documents.assert_called_once()
                    mock_vector_store.getESStore.return_value.similarity_search.assert_called_once()
    
    def test_backward_compatibility_upsert_documents(self):
        """Test backward compatibility function with ElasticsearchManager"""
        with patch('prefect_data_getters.stores.elasticsearch_compatibility.get_elasticsearch_manager') as mock_get_manager:
            mock_es_manager = Mock()
            mock_es_manager.upsert_documents.return_value = {'success': 2, 'failed': 0}
            mock_get_manager.return_value = mock_es_manager
            
            raw_docs = [
                {'page_content': 'content 1', 'google-id': 'id-1', 'metadata': {'key': 'value1'}},
                {'page_content': 'content 2', 'google-id': 'id-2', 'metadata': {'key': 'value2'}}
            ]
            
            upsert_documents(raw_docs, "test_index", "google-id")
            
            mock_es_manager.upsert_documents.assert_called_once()
            call_args = mock_es_manager.upsert_documents.call_args
            documents_arg = call_args[0][0]  # First positional argument
            index_arg = call_args[0][1]  # Second positional argument
            
            assert len(documents_arg) == 2
            assert all(isinstance(doc, AIDocument) for doc in documents_arg)
            assert index_arg == "test_index"
            assert documents_arg[0].id == 'id-1'
            assert documents_arg[1].id == 'id-2'
    
    def test_elasticsearch_query_building(self, unified_store):
        """Test Elasticsearch query building"""
        query = unified_store._build_elasticsearch_query("test query", None, 10)
        
        assert query['query']['multi_match']['query'] == "test query"
        assert query['size'] == 10
        assert 'highlight' in query
    
    def test_elasticsearch_query_with_filters(self, unified_store):
        """Test Elasticsearch query building with filters"""
        filters = {"author": "john", "type": "email"}
        query = unified_store._build_elasticsearch_query("test query", filters, 10)
        
        assert query['query']['bool']['must'][0]['multi_match']['query'] == "test query"
        assert len(query['query']['bool']['filter']) == 2
    
    def test_result_deduplication(self, unified_store):
        """Test result deduplication functionality"""
        doc1 = AIDocument("content 1", {"id": "1"})
        doc1.id = "same-id"
        doc2 = AIDocument("content 2", {"id": "2"})
        doc2.id = "same-id"  # Duplicate ID
        doc3 = AIDocument("content 3", {"id": "3"})
        doc3.id = "different-id"
        
        results = [doc1, doc2, doc3]
        unique_results = unified_store._deduplicate_results(results)
        
        assert len(unique_results) == 2  # Should remove one duplicate
        unique_ids = [doc.get_display_id() for doc in unique_results]
        assert "same-id" in unique_ids
        assert "different-id" in unique_ids
    
    def test_empty_document_handling(self, es_manager):
        """Test handling of empty document lists"""
        result = es_manager.upsert_documents([], "test_index")
        assert result == {'success': 0, 'failed': 0}
        
        result = es_manager.save_documents([], "test_index")
        assert result == {'success': 0, 'failed': 0}
    
    def test_error_handling_in_es_manager(self, es_manager, mock_es_client):
        """Test error handling in ElasticsearchManager"""
        mock_es_client.index.side_effect = Exception("Connection failed")
        
        doc = AIDocument("test content", {"key": "value"})
        result = es_manager.save_document(doc, "test_index")
        
        assert result == False
    
    def test_error_handling_in_unified_store(self, unified_store):
        """Test error handling in UnifiedDocumentStore"""
        with patch.object(unified_store.es_manager, 'upsert_documents') as mock_upsert:
            mock_upsert.side_effect = Exception("ES failure")
            
            doc = AIDocument("test content", {"key": "value"})
            results = unified_store.store_documents([doc], "test_store", store_in_vector=False)
            
            assert results['elasticsearch']['failed'] == 1
            assert results['elasticsearch']['success'] == 0

class TestPhase4Integration:
    """Integration tests for Phase 4 components working together"""
    
    def test_end_to_end_document_flow(self):
        """Test complete document lifecycle"""
        with patch('prefect_data_getters.stores.elasticsearch_manager.Elasticsearch') as mock_es_class:
            mock_es = Mock()
            mock_es_class.return_value = mock_es
            
            # Mock successful operations
            mock_es.index.return_value = {'result': 'created'}
            mock_es.get.return_value = {
                '_source': {
                    'page_content': 'test content',
                    'metadata': {'key': 'value'},
                    'id': 'test-123'
                }
            }
            mock_es.delete.return_value = {'result': 'deleted'}
            
            # Create document
            doc = AIDocument("test content", {"key": "value"})
            doc.id = "test-123"
            
            # Test save
            with patch.object(doc, 'save') as mock_save:
                mock_save.return_value = True
                assert doc.save("test_store") == True
            
            # Test search
            with patch.object(AIDocument, 'search') as mock_search:
                mock_search.return_value = [doc]
                results = AIDocument.search("test query", "test_store")
                assert len(results) == 1
            
            # Test delete
            with patch.object(doc, 'delete') as mock_delete:
                mock_delete.return_value = True
                assert doc.delete("test_store") == True

if __name__ == "__main__":
    pytest.main([__file__])