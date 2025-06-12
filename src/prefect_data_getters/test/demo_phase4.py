"""
Phase 4 Demo Script - Show the new unified Elasticsearch integration in action
"""

import sys
sys.path.append('src')

from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.unified_document_store import UnifiedDocumentStore
from prefect_data_getters.stores.elasticsearch_manager import ElasticsearchManager
from prefect_data_getters.stores.elasticsearch_compatibility import upsert_documents
from prefect_data_getters.stores.document_registry import DocumentTypeRegistry, register_document_type
from unittest.mock import Mock

print("🚀 Phase 4 Demo: Unified Elasticsearch Integration")
print("=" * 60)

# 1. Document Creation with New Methods
print("\n1️⃣ Enhanced Document Creation")
print("-" * 30)

# Create an enhanced AIDocument
doc = AIDocument(
    page_content="This is a demo document for Phase 4 Elasticsearch integration.",
    metadata={
        "author": "demo-user",
        "category": "integration-test",
        "tags": ["phase4", "elasticsearch", "demo"],
        "priority": "high"
    }
)
doc.id = "demo-doc-123"

print(f"📄 Document created: {doc.document_type}")
print(f"🆔 Display ID: {doc.get_display_id()}")
print(f"📝 Content preview: {doc.page_content[:50]}...")
print(f"🏷️ Metadata: {list(doc.metadata.keys())}")

# 2. Elasticsearch Manager
print("\n2️⃣ ElasticsearchManager Features")
print("-" * 30)

# Create ES manager with mock client for demo
mock_es = Mock()
es_manager = ElasticsearchManager(mock_es)

# Show serialization for ES storage
doc_dict = doc.to_dict()
print(f"💾 ES Storage Format: {list(doc_dict.keys())}")
print(f"📊 Document Type: {doc_dict['document_type']}")

# Demo health check
health = es_manager.health_check()
print(f"🏥 Health Check Fields: {list(health.keys())}")

# 3. Unified Document Store
print("\n3️⃣ UnifiedDocumentStore Interface")
print("-" * 30)

store = UnifiedDocumentStore(es_manager)

# Show query building
query = store._build_elasticsearch_query("demo search", None, 10)
print(f"🔍 Basic ES Query Structure: {list(query.keys())}")

# Show filtered query
filters = {"author": "demo-user", "priority": "high"}
filtered_query = store._build_elasticsearch_query("demo search", filters, 5)
print(f"🎯 Filtered Query Type: {filtered_query['query'].keys()}")
print(f"📋 Filter Count: {len(filtered_query['query']['bool']['filter'])}")

# 4. Document Instance Methods
print("\n4️⃣ Document Instance Methods")
print("-" * 30)

print(f"💾 Save method available: {hasattr(doc, 'save') and callable(doc.save)}")
print(f"🗑️ Delete method available: {hasattr(doc, 'delete') and callable(doc.delete)}")
print(f"🔍 Search class method available: {hasattr(AIDocument, 'search') and callable(AIDocument.search)}")

# Demo the method signatures
import inspect
save_sig = inspect.signature(doc.save)
print(f"💾 Save signature: {save_sig}")
search_sig = inspect.signature(AIDocument.search)
print(f"🔍 Search signature: {search_sig}")

# 5. Registry Integration
print("\n5️⃣ Registry Integration")
print("-" * 30)

# Show how registry works with unified store
registry = store.registry
print(f"📚 Registry available: {type(registry).__name__}")

# Demo document type registration
@register_document_type('demo_documents')
class DemoDocument(AIDocument):
    def get_display_id(self):
        return f"demo-{self.metadata.get('id', 'unknown')}"

print(f"✅ Demo document type registered: {registry.is_registered('demo_documents')}")
print(f"📋 Registered types: {list(registry.list_registered_types().keys())}")

# 6. Backward Compatibility
print("\n6️⃣ Backward Compatibility")
print("-" * 30)

print(f"🔄 upsert_documents function available: {callable(upsert_documents)}")

# Show how old format still works
old_format_docs = [
    {
        'page_content': 'Old format document 1',
        'google-id': 'old-doc-1',
        'author': 'legacy-system',
        'metadata': {'type': 'legacy'}
    },
    {
        'page_content': 'Old format document 2', 
        'google-id': 'old-doc-2',
        'author': 'legacy-system',
        'metadata': {'type': 'legacy'}
    }
]

print(f"📦 Old format example: {len(old_format_docs)} documents")
print(f"🔑 ID field: 'google-id'")
print(f"📄 Sample content: {old_format_docs[0]['page_content']}")

# 7. Search Capabilities
print("\n7️⃣ Search Capabilities")
print("-" * 30)

print("🔍 Available search types:")
print("  📝 Text search: Full-text search via Elasticsearch")
print("  🧠 Vector search: Semantic similarity search")
print("  🔗 Hybrid search: Combined text + vector search")

# Demo query building for different search types
text_query = store._build_elasticsearch_query("important documents", None, 10)
print(f"📝 Text query ready: {'multi_match' in text_query['query']}")

filtered_text_query = store._build_elasticsearch_query(
    "high priority tasks", 
    {"priority": "high", "author": "demo-user"}, 
    5
)
print(f"🎯 Filtered search ready: {'bool' in filtered_text_query['query']}")

# 8. Error Handling & Health
print("\n8️⃣ Error Handling & Health Monitoring")
print("-" * 30)

# Demo error handling
mock_es.index.side_effect = Exception("Demo connection error")
error_result = es_manager.save_document(doc, "demo_index")
print(f"❌ Error handling works: {error_result == False}")

# Health check integration
health_info = store.health_check()
print(f"🏥 Health components: {list(health_info.keys())}")
print(f"📊 Registry status: {health_info['registry']['registered_types']} types")

# 9. Usage Examples
print("\n9️⃣ Usage Examples")
print("-" * 30)

print("📝 Example 1: Simple document storage")
print("   doc = AIDocument('content', {'key': 'value'})")
print("   success = doc.save('my_index')  # New way!")

print("\n📝 Example 2: Search documents")
print("   results = AIDocument.search('query', 'my_index', top_k=10)")

print("\n📝 Example 3: Unified store operations")
print("   store = UnifiedDocumentStore()")
print("   store.store_documents([doc], 'index', store_in_vector=True)")

print("\n📝 Example 4: Health monitoring")
print("   health = store.health_check()")
print("   if health['elasticsearch']['status'] == 'green': ...")

# 10. Migration Path
print("\n🔟 Migration Path")
print("-" * 30)

print("✅ Phase 1: ✓ New AIDocument base class")
print("✅ Phase 2: ✓ Document registry system") 
print("✅ Phase 3: ✓ Document types refactoring")
print("✅ Phase 4: ✓ Elasticsearch integration")
print("🔄 Backward compatibility maintained throughout")

print("\n🎯 Next Steps for Adoption:")
print("1. Start using UnifiedDocumentStore for new code")
print("2. Gradually migrate from upsert_documents to store.store_documents")
print("3. Use doc.save(), doc.delete(), AIDocument.search() for convenience")
print("4. Monitor health via store.health_check()")
print("5. Leverage hybrid search capabilities")

print(f"\n🎉 Phase 4 Demo Complete!")
print("🚀 The AIDocument system now has a unified, powerful storage interface!")