import asyncio
from typing import List, Literal, Optional, Dict, Any
from langchain_elasticsearch import ElasticsearchStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.retrievers.document_compressors import LLMChainFilter
import stores.vectorstore as vectorstore
import utilities.constants as C
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from stores.documents import _AIDocument, SlackMessageDocument, convert_documents_to_ai_documents
from typing import List
from typing import List, Literal, Optional, Annotated
from datetime import datetime



class AcceptRejectDataStore(BaseModel):
    """Response indicating whether to accept or reject the datastore."""

    response: bool = Field(
        description="Indicates whether to use a document respond with true or false"
    )

class AdditionalEmbeddingsAndKeywords(BaseModel):
    keywords: List[str] = Field(
        description="A list of keywords that a document should contain to align it with the initial query"
    )
    embeddings: List[str] = Field(
        description="A list of phrases to turn into embeddings to search a RAG document store."
    )

class MultiSourceSearcher:
    def __init__(self) -> None:
        # Initialize embeddings
        self.embeddings = vectorstore.get_embeddings()

        # Initialize Elasticsearch stores for each index
        self.stores = [
            {
                "store": ElasticsearchStore(
                    es_url=C.ES_URL,
                    index_name=s["name"],
                    embedding=self.embeddings,
                ),
                "description": s["description"],
                "name": s["name"],
            }
            for s in C.data_stores
        ]


        # Initialize LLM for filtering
        self.llm = ChatOllama(model="llama3.2", temperature=0, num_ctx=120000)

        # Initialize LLMChainFilter
        self.llm_filter = LLMChainFilter.from_llm(self.llm)

    async def select_stores(self, query: str) -> List[ElasticsearchStore]:
        """Uses the LLM to select relevant data stores based on the query."""
        selected_stores = []
        for store_info in self.stores:
            if("slab" in store_info["name"].lower()):
                selected_stores.append(store_info["store"])
                continue
            response = self.llm.with_structured_output(AcceptRejectDataStore).invoke(
                input=f"The following describes a data store for a certain type of data.  Your job is to determine if it would be useful to query this data domain to get documents to help solve the original query. "
                  f"Does the following document store contain documents that would help solve the query?\n\nDescription: {store_info['description']}\n\nQuery: {query}\n\n"
                  "Reply only with 'true' or 'false' in the response field example: {'response': true}"
            )
            print(f"{response.response} for {store_info['name']}", flush=True)
            if response.response:
                selected_stores.append(store_info["store"])
        return selected_stores
    
    async def get_keywords_and_embeddings(self, query: str):
        return ChatOllama(model="llama3.2", temperature=0, num_ctx=120000, format='json', verbose=True).with_structured_output(AdditionalEmbeddingsAndKeywords).invoke(
            input=f"""
for the query that is meant to search across multiple data stores of 
documents, emails, slack messages and jira tickets.  
List out several key words that might be important for the documents to have 
as well as 5 different phrases that would be useful to turn into an embedding 
to pull out the most relevant documents from a RAG embedding vector document store.
You are tasked with generating clear, concise, and contextually rich search strings that will help retrieve documents, emails, Slack messages, and Jira tickets related to a specific query. The query is: 'What are the future plans for the data acquisition team?'
Please generate five distinct strings that summarize the query’s intent and could effectively serve as embeddings for retrieving the most relevant documents. Each string should:
Incorporate keywords supplied into some of these queries.
Reflect an understanding of project timelines, goals, or strategic direction.
Be specific enough to pull in precise information on goals, objectives, and future work.
Example: 
For the input query 'what is the role of engineering in our company?'
"""
"""
Output: {{"keywords": ["Engineering responsibilities", "Technical team functions", "Engineering department goals", "Product development process", "Role of engineering team", "Company-wide technical initiatives", "Innovation and engineering"], "embeddings":["Primary responsibilities and contributions of the engineering team in the company", "How the engineering department supports company goals and objectives", "Engineering's role in product development, innovation, and technical support", "Company-wide initiatives and functions driven by engineering", "The impact of engineering on company growth, product quality, and strategic direction"]}}
"""
f"""
Query to transform: {query}

            """
        )

    async def search(
        self,
        query: Annotated[str, "The input search query string"],
        top_k: Annotated[Optional[int], "Number of top results to return"] = 5,
        keywords: Annotated[Optional[List[str]], "List of keywords to filter the search results"] = None,
        from_date: Annotated[Optional[datetime], "Start date for the date range filter"] = None,
        to_date: Annotated[Optional[datetime], "End date for the date range filter"] = None,
        indexes: Annotated[Optional[List[str]], "List of specific vector store names to search"] = None,
        metadata_filter: Annotated[Optional[dict], "Metadata filters as key-value pairs"] = None,
        run_llm_reduction: Annotated[Optional[bool], "Whether to use LLM-based reduction on the results"] = False
    ) -> List[_AIDocument]:
        """
        Perform a multi-source search with keyword and embedding filters, optional date range, and LLM reduction.

        Returns:
            A list of `_AIDocument` objects representing the search results.
        """
        # Build keyword query for Elasticsearch, if keywords are provided
        keyword_filter = {
            "bool": {
                "should": [{"match": {"text": keyword}} for keyword in keywords],
                "minimum_should_match": 1,
            }
        } if keywords else None

        # Build date range filter for Elasticsearch, if dates are provided
        date_filter = {
            "range": {
                "post_datetime": {
                    "gte": from_date.isoformat() if from_date else None,
                    "lte": to_date.isoformat() if to_date else None
                }
            }
        } if from_date or to_date else None

        # Build metadata filter for Elasticsearch, if metadata_filter is provided
        metadata_filter_query = {
            "bool": {
                "must": [{"match": {f"metadata.{key}": value}} for key, value in metadata_filter.items()]
            }
        } if metadata_filter else None

        # Combine filters, if applicable
        es_filter = {"bool": {"must": []}}
        if keyword_filter:
            es_filter["bool"]["must"].append(keyword_filter)
        if date_filter:
            es_filter["bool"]["must"].append(date_filter)
        if metadata_filter_query:
            es_filter["bool"]["must"].append(metadata_filter_query)
        if not es_filter["bool"]["must"]:
            es_filter = None  # Avoid adding empty filters

        # Use the LLM to generate additional keywords and embeddings
        additional = await self.get_keywords_and_embeddings(query=query)

        # Select stores if indexes are not explicitly provided
        selected_stores = [store for store in self.stores if store["name"] in indexes] if indexes else await self.select_stores(query)

        # Create tasks for similarity and keyword searches across each selected store
        search_results = []
        additional.embeddings.extend([query])  # Add the original query to embeddings
        for q in additional.embeddings:
            qemb = self.embeddings.embed_query(q)
            for store_info in selected_stores:
                store = store_info["store"]
                temp_results = store.similarity_search_by_vector_with_relevance_scores(qemb, top_k, filter=es_filter, num_candidates=10*top_k)
                temp_results_d = [d[0] for d in temp_results]
                docs = convert_documents_to_ai_documents(temp_results_d, store._store.index)
                if("slack" in store_info["name"]):
                    tdocs = []
                    for d in docs:
                        td = extend_slack_message(d)
                        tdocs.append(td)
                    docs = tdocs
                for i in range(len(temp_results)):
                    search_results.append((docs[i], temp_results[i][1]))

        # Sort results by relevance score in descending order
        search_results.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate results based on document ID
        combined_results = [d[0] for d in search_results]
        combined_results = list({c.id: c for c in combined_results}.values())

        # Apply LLM reduction if requested
        docs = []
        if run_llm_reduction:
            for d in combined_results:
                docs.extend(self.llm_filter.compress_documents([d], query))
                if len(docs) >= top_k:
                    break
        else:
            docs = combined_results[:top_k]

        # Return sorted filtered results
        return docs
    from datetime import timedelta
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

def extend_slack_message(slack_message: SlackMessageDocument, minutes_before_after: int = 120) -> SlackMessageDocument:
    """
    Extend a Slack message by retrieving related context messages from the same channel.
    If it's part of a thread, retrieve all messages from the thread.
    Otherwise, retrieve messages within a time range around the timestamp.

    Args:
        slack_message (SlackMessageDocument): The original Slack message document.
        minutes_before_after (int): Time range (in minutes) before and after the original message's timestamp.

    Returns:
        SlackMessageDocument: The updated Slack message document with extended context.
    """
    es_client = Elasticsearch(C.ES_URL)  # Initialize Elasticsearch client

    # Extract metadata
    ts = slack_message._get_metadata("ts")
    ts_thread = slack_message._get_metadata("thread_ts")
    channel = slack_message._get_metadata("channel")
    if not ts or not channel:
        raise ValueError("Missing 'ts' or 'channel' metadata in the Slack message document.")

    # Convert timestamp to datetime
    ts_datetime = datetime.utcfromtimestamp(float(ts))

    if not ts_thread:
        # Define time range
        from_time = ts_datetime - timedelta(minutes=minutes_before_after)
        to_time = ts_datetime + timedelta(minutes=minutes_before_after)

        # Query Elasticsearch for messages in the same channel within the time range
        search_query = Search(using=es_client, index="slack_messages").query(
            "bool",
            must=[
                {"term": {"metadata.channel.keyword": channel}},
                {
                    "range": {
                        "metadata.ts_iso": {
                            "gte": (from_time),
                            "lte": (to_time),
                        }
                    }
                },
            ],
        ).sort("metadata.ts")

        response = search_query.execute()

        # Collect and format messages
        context_messages = [
            f"[{datetime.fromtimestamp(float(msg.metadata['ts']))}] {msg.metadata['user'] if "user" in msg.metadata.keys() else "NoName"}: {msg.text}"
            for msg in response.hits
        ]
    else:
        # Query Elasticsearch for messages in the same thread and channel
        search_query = Search(using=es_client, index="slack_messages").query(
            "bool",
            must=[
                {"term": {"metadata.channel.keyword": channel}},
                {"term": {"metadata.thread_ts": str(ts_thread)}},
            ],
        ).sort("metadata.ts")

        response = search_query.execute()

        # Collect and format thread messages
        context_messages = [
            f"[{datetime.fromtimestamp(float(msg.metadata['ts']))}] {msg.metadata['user'] if "user" in msg.metadata.keys() else "NoName"}: {msg.text}"
            for msg in response.hits
        ]

    # Extend the original message text with formatted context messages
    slack_message.set_page_content("\n".join(context_messages))
    # slack_message.text = extended_text

    return slack_message


