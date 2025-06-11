from elasticsearch import Elasticsearch, helpers
import prefect_data_getters.utilities.constants as C

es = Elasticsearch(C.ES_URL)
# TODO: make this private and go through the AI doc
# right now this is just used by gmail, thank goodness.
def upsert_documents(docs: list[dict], index_name: str, id_field: str):
    actions = []

    for doc in docs:
        doc_id = doc[id_field]
        action = {
            "_op_type": "update",
            "_index": index_name,
            "_id": doc_id,
            "doc": doc,
            "doc_as_upsert": True 
        }
        actions.append(action)

    helpers.bulk(es, actions)
