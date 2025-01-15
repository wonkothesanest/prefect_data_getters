import os
import shutil
from prefect import flow, task
from langchain.schema import Document
from typing import List
from prefect_data_getters.exporters import add_default_metadata
from prefect_data_getters.exporters.gmail import process_message
from prefect_data_getters.utilities import constants as C  
from prefect_data_getters.utilities.constants import MBOX_FILE_PATH
from prefect_data_getters.stores.vectorstore import batch_process_and_store, get_embeddings_and_vectordb
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
    base_dir = MBOX_FILE_PATH  # Now this should be a directory
    if not os.path.isdir(base_dir):
        print(f"ERROR: {base_dir} is not a directory.")
        return

    processable_dirs = []
    
    # Identify top-level directories that are processable
    for entry in os.listdir(base_dir):
        dir_path = os.path.join(base_dir, entry)
        if os.path.isdir(dir_path):
            processing_file = os.path.join(dir_path, "processing")
            processed_file = os.path.join(dir_path, "processed")

            # Check for "processing" or "processed" markers
            if os.path.exists(processing_file) or os.path.exists(processed_file):
                # Skip this directory
                print(f"Skipping {dir_path} because it's already processing or processed.")
                continue
            
            # This directory is processable
            processable_dirs.append(dir_path)

    # Process each directory
    for dir_path in processable_dirs:
        processing_file = os.path.join(dir_path, "processing")
        processed_file = os.path.join(dir_path, "processed")

        # Create the processing file
        with open(processing_file, 'w') as f:
            f.write("")

        # Find all "ME" files in this directory (top-level or deeper if needed)
        # Adjust the pattern if ME files are only at top-level or nested
        me_files = []
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file == "ME" or file == "INBOX":
                    me_files.append(os.path.join(root, file))

        all_docs = []
        # Process each ME file
        for me_file in me_files:
            docs = process_mbox_file(me_file)
            all_docs.extend(docs)

        # Log the number of processed messages
        print(f"Number of email messages processed in {dir_path}: {len(all_docs)}")

        # Store documents in vector store
        if len(all_docs) > 0:
            store_documents_in_vectorstore(all_docs)

        # Remove the processing file and create the processed file
        if os.path.exists(processing_file):
            os.remove(processing_file)
        with open(processed_file, 'w') as f:
            f.write("")

    # Finally, delete all top-level directories that have been processed
    for entry in os.listdir(base_dir):
        dir_path = os.path.join(base_dir, entry)
        if os.path.isdir(dir_path):
            processed_file = os.path.join(dir_path, "processed")
            if os.path.exists(processed_file):
                print(f"Removing processed directory: {dir_path}")
                shutil.rmtree(dir_path, ignore_errors=True)

if __name__ == '__main__':
    gmail_mbox_backup_flow()
