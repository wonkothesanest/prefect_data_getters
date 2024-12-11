import json
import os
from langchain.schema import Document
import glob
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import TextSplitter
from src.stores.vectorstore import get_embeddings_and_vectordb
from src.utilities import parse_date


def process_slab_docs(backup_dir, split:bool = True) -> list[Document]:
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



def __process_slab_docs(doc_file:str, meta_file: str,  semantic_chunker: TextSplitter = None)-> list[Document]:
    
    with open(meta_file) as f:
        slab_meta = json.load(f)
        slab_meta = slab_meta["data"]["post"]
    topics = []
    for t in slab_meta.get("topics"):
        root = t.get("name")
        try:
            topics.append(f"{" / ".join([tt.get("name") for tt in t.get("ancestors")])} /  {root}")
        except: pass
    # Could get root topic where parent is null in allTopics.  if helpful later
    metadata  = {
        "document_id": slab_meta.get("id"),
        "title": slab_meta.get("title"),
        "owner": slab_meta.get("owner").get("name"),
        "contributors": ", ".join([c.get("name") for c in slab_meta.get("contributors")]),
        "topics": " ## ".join(topics),
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
                    id = f"{metadata["document_id"]}_{idx}"
                    idx += 1
                    docs.append(Document(id=id, page_content=strc, metadata=metadata))
        else:
            metadata.update({"type": "slab_document"})
            id = metadata["document_id"]
            docs.append(Document(id=id, page_content=content, metadata = metadata))

    return docs
