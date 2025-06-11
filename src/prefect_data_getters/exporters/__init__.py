from langchain.schema import Document
from datetime import datetime

# TODO this is tightly part of the document not the getters.
def add_default_metadata(docs: list[Document]):
    """
    For all documents we want some metadata that is the same 
        ingested_timestamp
        must have id

    """
    ingested_timestamp = datetime.now().isoformat()
    for d in docs:
        d.metadata.update({"ingestion_timestamp": ingested_timestamp})
    return docs