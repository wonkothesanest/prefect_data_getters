import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from utilities.constants import VECTOR_STORE_DIR
from langchain_elasticsearch import ElasticsearchStore

from langchain_community.vectorstores import ElasticVectorSearch
import os
import utilities.constants as C

# Constants
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ============================
#  Embeddings and Vector Store
# ============================
def get_embeddings_and_vectordb(collection_name: C.VECTOR_STORE_NAMES, basedir=VECTOR_STORE_DIR, model_name=EMB_MODEL) -> tuple[HuggingFaceEmbeddings, Chroma]:
    """Returns the HuggingFace embeddings and Chroma vector store."""
    embeddings = get_embeddings(model_name)
    vectorstore = _get_vs(collection_name)
    return embeddings, vectorstore

def get_slack() -> Chroma:
    """Returns Chroma vector store for Slack messages."""
    return _get_vs("slack_messages")

def get_slab() -> Chroma:
    """Returns Chroma vector store for Slab documents."""
    return _get_vs("slab_docs")

def _get_vs(collection_name: C.VECTOR_STORE_NAMES) -> Chroma:
    """Creates and returns a Chroma vector store for the given collection name."""
    return Chroma(
        collection_name=collection_name,
        persist_directory=os.path.join(VECTOR_STORE_DIR, collection_name),
        embedding_function=get_embeddings()
    )

def get_embeddings(model_name=EMB_MODEL) -> HuggingFaceEmbeddings:
    """Returns HuggingFace embeddings using the specified model."""
    return HuggingFaceEmbeddings(model_name=model_name)

# ============================
#  Batch Process and Store
# ============================
def batch_process_and_store(documents: list[Document],  vectorstore: Chroma, batch_size: int=1000):
    """Processes documents in batches and adds them to the vector store."""
    documents = _deduplicate_based_on_id(documents)
    ESVectorStore(vectorstore._collection_name).batch_process_and_store(documents=documents, batch_size=batch_size)
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        vectorstore.add_documents(batch)

def _deduplicate_based_on_id(docs: list[Document]) -> list[Document]:
    s = set()
    ret_docs = []
    for idx,d in enumerate(docs):
        if(d.id != None):
            if(d.id not in s):
                s.add(d.id)
                ret_docs.append(d)
            else:
                print(f"Duplicate document of {d.id} found")
    return ret_docs



class ESVectorStore():
    def __init__(self, index_name: C.VECTOR_STORE_NAMES):
        self._vector_store = ElasticsearchStore(
            es_url=C.ES_URL,
            index_name=index_name,
            embedding=get_embeddings(),
        )
    def batch_process_and_store(self, documents: list[Document], batch_size: int=1000):
        """Processes documents in batches and adds them to the vector store."""
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            self._vector_store.add_documents(batch)

    def getESStore(self) -> ElasticsearchStore:
        return self._vector_store