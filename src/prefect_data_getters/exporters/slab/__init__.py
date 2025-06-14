"""
DEPRECATED: Legacy Slab exporter module.

This module is deprecated. Please use the new SlabExporter class:

from prefect_data_getters.exporters.slab_exporter import SlabExporter

# New usage:
exporter = SlabExporter()
raw_data = exporter.export(backup_dir)
documents = exporter.process(raw_data)

# Or use convenience method:
documents = exporter.export_documents(backup_dir)
"""

import warnings
import json
import os
from langchain.schema import Document
import glob
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import TextSplitter
from prefect_data_getters.stores.vectorstore import get_embeddings_and_vectordb
from prefect_data_getters.utilities import parse_date

# Import the new exporter for backward compatibility
from prefect_data_getters.exporters.slab_exporter import SlabExporter

# Global exporter instance for backward compatibility
_slab_exporter_instance = None

def get_slab_exporter() -> SlabExporter:
    """
    Get a SlabExporter instance for backward compatibility.
    
    Returns:
        SlabExporter: Configured Slab exporter instance
    """
    global _slab_exporter_instance
    if _slab_exporter_instance is None:
        _slab_exporter_instance = SlabExporter()
    return _slab_exporter_instance

def process_slab_docs(backup_dir, split: bool = True) -> list[Document]:
    """
    DEPRECATED: Process Slab documents using the legacy interface.
    
    This function is deprecated. Please use SlabExporter directly:
    
    from prefect_data_getters.exporters.slab_exporter import SlabExporter
    
    exporter = SlabExporter({"split_documents": split})
    documents = list(exporter.export_documents(backup_dir))
    
    Args:
        backup_dir: Directory containing Slab backup files
        split: Whether to split documents into chunks
        
    Returns:
        List of Document objects
    """
    warnings.warn(
        "process_slab_docs is deprecated. Use SlabExporter class instead. "
        "See: from prefect_data_getters.exporters.slab_exporter import SlabExporter",
        DeprecationWarning,
        stacklevel=2
    )
    
    exporter = SlabExporter({"split_documents": split})
    return list(exporter.export_documents(backup_dir))
    embeddings_model, vectorstore = get_embeddings_and_vectordb("slab_docs")
    if(split):
        semantic_chunker = SemanticChunker(embeddings=embeddings_model,breakpoint_threshold_amount=50, number_of_chunks=10)
    else:
        semantic_chunker = None
    
    slab_files = glob.glob(os.path.join(backup_dir, "*.md"))
    processed_documents = []
    for f in slab_files:
        docs = __process_slab_docs(f, f.replace(".md", ".json"), semantic_chunker)
        processed_documents.extend(docs)
        # [print(len(doc.page_content)) for doc in docs]
    print("number of documents processed: ", len(processed_documents))
    return processed_documents

def __get_all_users(backup_dir):
    with open(os.path.join(os.path.dirname(backup_dir), 'allUsers.json')) as f:
        data = json.load(f)
    users = {user['id']: user for user in data['data']['session']['organization']['users']}
    return users

def __get_all_topics(backup_dir):
    with open(os.path.join(os.path.dirname(backup_dir), 'allTopics.json')) as f:
        data = json.load(f)
    topics = {topic['id']: topic for topic in data['data']['session']['organization']['topics']}
    return topics

def __get_user(user_id, users):
    return users.get(user_id)

def __get_user_info(user_id, users):
    user = __get_user(user_id, users)
    if user:
        name = user.get("name")
        email = user.get("email")
        return f"{name} - {email}" if email else name
    return None

def __get_topic(topic_id, topics):
    return topics.get(topic_id)

def __get_topic_ancestors(topic_id, topics):
    ancestors = []
    current_topic = __get_topic(topic_id, topics)
    while current_topic and current_topic.get('parent'):
        parent_id = current_topic['parent']['id']
        parent_topic = __get_topic(parent_id, topics)
        if parent_topic:
            ancestors.append(parent_topic)
            current_topic = parent_topic
        else:
            break
    return ancestors

def __process_slab_docs(doc_file:str, meta_file: str,  semantic_chunker: TextSplitter = None)-> list[Document]:
    backup_dir = os.path.dirname(doc_file)
    users = __get_all_users(backup_dir)
    topics = __get_all_topics(backup_dir)
    
    with open(meta_file) as f:
        slab_meta = json.load(f)
        slab_meta = slab_meta["data"]["post"]
    topics_list = []
    for t in slab_meta.get("topics"):
        root = __get_topic(t.get("id"), topics).get("name")
        try:
            ancestors = __get_topic_ancestors(t.get("id"), topics)
            ancestor_names = [ancestor.get("name") for ancestor in ancestors]
            ancestor_names.reverse()
            topics_list.append(f"{' / '.join(ancestor_names)} / {root}")
        except: pass
    # Could get root topic where parent is null in allTopics if helpful later
    metadata  = {
        "document_id": slab_meta.get("id"),
        "title": slab_meta.get("title"),
        "owner": __get_user_info(slab_meta.get("owner").get("id"), users),
        "contributors": ", ".join([__get_user_info(c.get("id"), users) for c in slab_meta.get("contributors")]),
        "topics": " ## ".join(topics_list),
        "updated_at": parse_date(slab_meta.get("updatedAt")),
        "created_at": parse_date(slab_meta.get("insertedAt")),
        "slab_type": slab_meta.get("__typename"),

    }
    docs = []
    with open(doc_file) as ff:
        content = ff.read()
        if(semantic_chunker):
            metadata.update({"type": "slab_chunk"})
            idx = 0
            for strc in semantic_chunker.split_text(content):
                if(len(strc) != 0):
                    id = f"{metadata['document_id']}_{idx}"
                    idx += 1
                    docs.append(Document(id=id, page_content=strc, metadata=metadata))
        else:
            metadata.update({"type": "slab_document"})
            id = metadata["document_id"]
            docs.append(Document(id=id, page_content=content, metadata = metadata))

    return docs
