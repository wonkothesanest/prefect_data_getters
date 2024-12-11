
import asyncio
from datetime import datetime
from typing import Annotated, List, Optional

from src.stores.documents import _AIDocument
from src.stores.rag_man import MultiSourceSearcher
import src.utilities.constants as C

from langchain.tools import tool


searcher = MultiSourceSearcher()

@tool("Search with simple inputs for an LLM to help fill in the needed information based on an input query")
def search_with_llm(query:Annotated[str, "Input query to generate several more vector search queries to query vector databases"],
           keywords: Annotated[list[str], "List of keywords that the documents must have one of to be considered."]
           ) -> list[_AIDocument]:
    """Search tool to search across multiple data sources including documentation, jira tickets, slack messages and email messages"""
    # print(f"Received Query: {query} with keywords {keywords}")
    docs = asyncio.run( searcher.search(query, keywords=keywords, top_k=15))
    
    return docs

@tool()
def search_jira_tickets(
    self,
    query: Annotated[str, "The input search query string"],
    top_k: Annotated[int, "Number of top results to return"] = 5,
    keywords: Annotated[Optional[List[str]], "List of keywords to filter the search results"] = None,
    from_date: Annotated[Optional[datetime], "Start date for the date range filter"] = None,
    to_date: Annotated[Optional[datetime], "End date for the date range filter"] = None,
    indexes: Annotated[Optional[List[C.VECTOR_STORE_NAMES]], "List of specific vector store names to search"] = None,
    run_llm_reduction: Annotated[bool, "Whether to use LLM-based reduction on the results"] = False
) -> List[_AIDocument]:
    """Search across engineering jira tickets"""
    return asyncio.run(
        searcher.search(
            ...,
            indexes=[C.VECTOR_STORE_NAMES["jira_issues"]],
        ))

@tool()
def search_emails(
    query: Annotated[str, "The input search query string"],
    top_k: Annotated[int, "Number of top results to return"] = 5,
    keywords: Annotated[Optional[List[str] | str], "List of keywords to filter the search results"] = None,
    from_date: Annotated[Optional[str], "Start date for the date range filter"] = None,
    to_date: Annotated[Optional[str], "End date for the date range filter"] = None,
) -> List[_AIDocument]:
    """Search across engineering Manager's emails. This is to search Dusty's email account. Useful for finding out project information and progress."""
    return asyncio.run(
        searcher.search(
            ...,
            indexes=[C.VECTOR_STORE_NAMES["email_messages"]],
        ))