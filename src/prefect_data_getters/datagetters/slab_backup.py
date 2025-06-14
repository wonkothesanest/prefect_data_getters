from prefect import flow, task
from langchain.schema import Document
from typing import List
from prefect_data_getters.utilities.constants import SLAB_BACKUP_DIR
from prefect_data_getters.stores.document_types.slab_document import SlabDocument, SlabChunkDocument
from prefect_data_getters.exporters.slab_exporter import SlabExporter


@task
def fetch_slab_documents(backup_dir: str) -> List[dict]:
    """Fetch raw Slab document data from backup directory."""
    slab_exporter = SlabExporter()
    slab_docs = slab_exporter.export(backup_dir=backup_dir)
    return list(slab_docs)

@task
def process_documents_to_slab_documents(raw_docs: List[dict]) -> List[Document]:
    """Process raw Slab data into Document objects."""
    slab_exporter = SlabExporter()
    documents = list(slab_exporter.process(iter(raw_docs)))
    return documents

@task
def store_document_chunks_in_vectorstore(documents: List[Document]):
    """Store Slab document chunks in vector store."""
    chunk_docs = [doc for doc in documents if doc.metadata.get("type") == "slab_chunk"]
    if chunk_docs:
        SlabChunkDocument.save_documents(
            docs=chunk_docs,
            store_name="slab_document_chunks",
            also_store_vectors=True
        )

@task
def store_full_documents_in_vectorstore(documents: List[Document]):
    """Store full Slab documents in vector store."""
    full_docs = [doc for doc in documents if doc.metadata.get("type") == "slab_document"]
    if full_docs:
        SlabDocument.save_documents(
            docs=full_docs,
            store_name="slab_documents",
            also_store_vectors=True
        )


@flow(name="slab-backup-flow", log_prints=True, timeout_seconds=3600)
def slab_backup_flow():
    # Step 1: Fetch raw Slab documents
    raw_documents = fetch_slab_documents(SLAB_BACKUP_DIR)

    # Step 2: Process documents into Document objects
    documents = process_documents_to_slab_documents(raw_documents)

    # Separate chunks and full documents
    chunk_docs = [doc for doc in documents if doc.metadata.get("type") == "slab_chunk"]
    full_docs = [doc for doc in documents if doc.metadata.get("type") == "slab_document"]

    # Log the number of processed documents
    print(f"Number of document chunks processed: {len(chunk_docs)}")
    print(f"Number of full documents processed: {len(full_docs)}")

    # Step 3: Store documents in vector store
    store_document_chunks_in_vectorstore(chunk_docs)
    store_full_documents_in_vectorstore(full_docs)

if __name__ == '__main__':
    slab_backup_flow()

