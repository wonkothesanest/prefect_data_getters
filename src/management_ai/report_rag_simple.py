from datetime import datetime, timedelta
from prefect_data_getters.stores.rag_man import MultiSourceSearcher
from management_ai.reporting import run_report, write_reports

from prefect_data_getters.utilities.people import HYPERION,person

from prefect_data_getters.utilities.timing import print_human_readable_delta
import prefect_data_getters.utilities.constants as C
import asyncio

searcher = MultiSourceSearcher()

query = """
For the metadata verification (MDV) hardening project, please provide a summary of the current status, including any issues or challenges faced, and the next steps to be taken. Include any relevant information from the following sources: email messages, Jira issues, Slack messages, and Slab documents.
The report should be concise and focused on the MDV hardening project, highlighting key points and actionable items. Please ensure that the information is up-to-date and relevant to the current state of the project.
The report should be structured as follows:
1. Project Overview
2. Current Status
3. Issues and Challenges
4. Next Steps
5. Milestones and Deadlines
"""
doc_query = """
Metadata Verification (MDV).
"""



def generate_rag_report():
    
    print(f"Running: {query}")
    r = run_report(
        docs= _get_documents(doc_query),
        report_message= query,
    )
    write_reports([r], f"adhoc report", "rag")
    


def _get_documents(document_query):

    all_docs = asyncio.run( searcher.search(
        query=document_query,
        indexes=C.ALL_INDEX_LIST[:-1],
        from_date=datetime.now() - timedelta(weeks=6),
        to_date=datetime.now(),
        top_k=50
    ))
    all_docs.sort(key=lambda x: x.search_score, reverse=True)
    return all_docs[:15]


if __name__ == "__main__":
    generate_rag_report()