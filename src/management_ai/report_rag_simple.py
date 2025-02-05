from datetime import datetime, timedelta
from prefect_data_getters.stores.rag_man import MultiSourceSearcher
from management_ai.reporting import run_report, write_reports

from prefect_data_getters.utilities.people import HYPERION,person

from prefect_data_getters.utilities.timing import print_human_readable_delta
import prefect_data_getters.utilities.constants as C
import asyncio

searcher = MultiSourceSearcher()

query = """
I want a detailed list of jira tasks and the epic details I need to create
in order to accomplish what we need to do for the onboarding asset sync process
that we are doing to move from Zendesk to Sales Force Service cloud
"""
doc_query = """
Zendesk to Sales Force Service Cloud asset and contact sync
"""



def generate_rag_report():
    
    print(f"Running: {query}")
    r = run_report(
        docs= _get_documents(doc_query),
        report_message= query,
    )
    write_reports([r], f"adhoc report")
    


def _get_documents(document_query):

    all_docs = asyncio.run( searcher.search(
        query=document_query,
        indexes=C.ALL_INDEXES,
        top_k=10
    ))
    all_docs.sort(key=lambda x: x.search_score, reverse=True)
    return all_docs[:15]


if __name__ == "__main__":
    generate_rag_report()