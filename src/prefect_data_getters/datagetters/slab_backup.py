from prefect import flow, task
from langchain.schema import Document
from typing import List
from prefect_data_getters.exporters import add_default_metadata
from prefect_data_getters.utilities.constants import SLAB_BACKUP_DIR
from prefect_data_getters.stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb
from langchain_community.vectorstores.utils import filter_complex_metadata
from prefect_data_getters.exporters.slab import process_slab_docs


@task
def process_data_dir(split) -> List[Document]:
    #TODO: documents do not have (ie null) updated or created, also remove add default metadata
    # Make this all a partof the document processing.
    documents = process_slab_docs(SLAB_BACKUP_DIR, split=split)

    return filter_complex_metadata(add_default_metadata(documents))

@task
def store_document_chunks_in_vectorstore(documents: List[Document]):
    batch_size = 1000 
    embeddings, vectorstore = get_embeddings_and_vectordb("slab_document_chunks")
    batch_process_and_store(documents, vectorstore)


@task
def store_full_documents_in_vectorstore(documents: List[Document]):
    batch_size = 1000 
    embeddings, vectorstore = get_embeddings_and_vectordb("slab_documents")
    batch_process_and_store(documents, vectorstore)


@flow(name="slab-backup-flow", log_prints=True, timeout_seconds=3600)
def slab_backup_flow():
    # Step 1: Process the data dir
    documents_split = process_data_dir(True)
    documents_full = process_data_dir(False)


    # Log the number of processed messages
    print(f"Number of document chunks processed: {len(documents_split)}")
    print(f"Number of full documents processed: {len(documents_full)}")

    # Step 2: Store documents in vector store
    store_document_chunks_in_vectorstore(documents_split)
    store_full_documents_in_vectorstore(documents_full)

if __name__ == '__main__':
    slab_backup_flow()
