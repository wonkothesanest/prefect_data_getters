from prefect import flow, task
from langchain.schema import Document
from typing import List
from exporters import add_default_metadata
from exporters.gmail import process_message
import utilities.constants as C  
from utilities.constants import MBOX_FILE_PATH
from stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb
import mailbox
from langchain_community.vectorstores.utils import filter_complex_metadata


@task
def process_mbox_file(mbox_file_path: str) -> List[Document]:
    documents = []
    mbox = mailbox.mbox(mbox_file_path)

    for idx, message in enumerate(mbox):
        document = process_message(message)
        documents.append(document)
    return filter_complex_metadata(add_default_metadata(documents))

@task
def store_documents_in_vectorstore(documents: List[Document]):
    embeddings, vectorstore = get_embeddings_and_vectordb("email_messages")
    batch_size = 1000  # Adjust based on your needs
    batch_process_and_store(documents, vectorstore)


@flow(name="gmail-mbox-backup-flow", log_prints=True)
def gmail_mbox_backup_flow():
    # Step 1: Process the mbox file
    documents = process_mbox_file(MBOX_FILE_PATH)

    # Log the number of processed messages
    print(f"Number of email messages processed: {len(documents)}")

    # Step 2: Store documents in vector store
    store_documents_in_vectorstore(documents)

if __name__ == '__main__':
    gmail_mbox_backup_flow()
