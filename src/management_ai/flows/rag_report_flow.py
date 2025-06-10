from datetime import datetime
from prefect import flow, task
import sys
import os
import asyncio

# Add the parent directory to the path so we can import from management_ai
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from management_ai.reporting import run_report, write_reports
import prefect_data_getters.utilities.constants as C
from prefect_data_getters.stores.rag_man import MultiSourceSearcher

@task
def get_documents(document_query):
    """Task to get documents for a query"""
    searcher = MultiSourceSearcher()
    all_docs = asyncio.run(searcher.search(
        query=document_query,
        indexes=C.ALL_INDEXES,
        top_k=10
    ))
    all_docs.sort(key=lambda x: x.search_score, reverse=True)
    return all_docs[:15]

@flow(name="RAG Report Flow", timeout_seconds=3600)
def rag_report_flow(
    query: str = "I need information about recent projects",
    doc_query: str = ""
):
    """
    Flow to generate RAG (Retrieval Augmented Generation) reports
    
    Args:
        query: The main query to generate the report (default: "I need information about recent projects")
        doc_query: The query to use for document retrieval (default: "", which means use the main query)
    """
    # If no doc_query is provided, use the main query
    if not doc_query:
        doc_query = query
    
    print(f"Running query: {query}")
    print(f"Document query: {doc_query}")
    
    # Get documents
    docs = get_documents(doc_query)
    
    # Generate report
    report = run_report(
        docs=docs,
        report_message=query,
    )
    
    # Write report
    write_reports([report], f"RAG Report - {query[:30]}...", "rag")
    
    return "RAG report generated successfully"

if __name__ == "__main__":
    rag_report_flow()