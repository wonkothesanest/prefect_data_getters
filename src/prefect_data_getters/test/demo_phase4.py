"""
Phase 4 Demo Script - Show the new direct store access architecture in action
"""

import sys
sys.path.append('src')

from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.elasticsearch_manager import ElasticsearchManager
from prefect_data_getters.stores.elasticsearch_compatibility import upsert_documents
from prefect_data_getters.stores.document_registry import DocumentTypeRegistry, register_document_type
from prefect_data_getters.stores.vectorstore import ESVectorStore
from unittest.mock import Mock

print("🚀 Phase 4 Demo: Direct Store Access Architecture")
print("=" * 60)

# 1. Document Creation with New Methods
print("\n1️⃣ Enhanced Document Creation")
print("-" * 30)

# Create an enhanced AIDocument
doc = AIDocument(
    page_content="This is a demo document for Phase 4 direct store access.",
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

# 2. ElasticsearchManager Features
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

# 3. Direct AIDocument Methods
print("\n3️⃣ Direct AIDocument Store Access")
print("-" * 30)

print(f"💾 Save method signature: {AIDocument.save.__doc__.split('.')[0]}...")
print(f"🗑️ Delete method signature: {AIDocument.delete.__doc__.split('.')[0]}...")
print(f"🔍 Search method signature: {AIDocument.search.__doc__.split('.')[0]}...")

# Show new method capabilities
print("\n📋 New Save Options:")
print("   • also_store_vectors=True  -> Store in both text and vector indices")
print("   • also_store_vectors=False -> Store only in text index for performance")

print("\n🔍 New Search Types:")
print("   • search_type='text'   -> Full-text Elasticsearch search")
print("   • search_type='vector' -> Semantic vector search")
print("   • search_type='hybrid' -> Combined text + vector search")

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

# Show direct registry usage
registry = DocumentTypeRegistry
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

# Demo search method calls
print(f"📝 Text search available: {hasattr(AIDocument, 'search')}")
print(f"🧠 Vector search supported: search_type='vector'")
print(f"🔗 Hybrid search supported: search_type='hybrid'")

# 8. Error Handling & Health
print("\n8️⃣ Error Handling & Health Monitoring")
print("-" * 30)

# Demo error handling
mock_es.index.side_effect = Exception("Demo connection error")
error_result = es_manager.save_document(doc, "demo_index")
print(f"❌ Error handling works: {error_result == False}")

# Health check via ES manager
health_info = es_manager.health_check()
print(f"🏥 Health check available: {type(health_info) == dict}")
print(f"📊 ES Health fields: {list(health_info.keys())}")

# 9. Usage Examples
print("\n9️⃣ Usage Examples")
print("-" * 30)

print("📝 Example 1: Simple document storage")
print("   doc = AIDocument('content', {'key': 'value'})")
print("   success = doc.save('my_index')  # Direct store access!")

print("\n📝 Example 2: Search documents")
print("   results = AIDocument.search('query', 'my_index', search_type='text')")

print("\n📝 Example 3: Vector storage")
print("   success = doc.save('my_index', also_store_vectors=True)")

print("\n📝 Example 4: Hybrid search")
print("   results = AIDocument.search('query', 'my_index', search_type='hybrid')")

print("\n📝 Example 5: ElasticsearchManager direct usage")
print("   es_manager = ElasticsearchManager()")
print("   success = es_manager.save_document(doc, 'index')")

# 10. Migration Path
print("\n🔟 Migration Path")
print("-" * 30)

print("✅ Phase 1: ✓ New AIDocument base class")
print("✅ Phase 2: ✓ Document registry system")
print("✅ Phase 3: ✓ Document types refactoring")
print("✅ Phase 4: ✓ Direct store access (UnifiedDocumentStore removed)")
print("🔄 Backward compatibility maintained throughout")

print("\n🎯 Next Steps for Adoption:")
print("1. Use doc.save(), doc.delete(), AIDocument.search() for direct access")
print("2. Gradually migrate from upsert_documents to ElasticsearchManager")
print("3. Leverage search_type options: 'text', 'vector', 'hybrid'")
print("4. Monitor health via es_manager.health_check()")
print("5. Use also_store_vectors=True for semantic search capabilities")

print(f"\n🎉 Phase 4 Demo Complete!")
print("🚀 The AIDocument system now has a unified, powerful storage interface!")