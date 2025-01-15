import asyncio
from typing import List, Literal, Optional, Dict, Any
from langchain_elasticsearch import ElasticsearchStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.retrievers.document_compressors import LLMChainFilter
import prefect_data_getters.stores.vectorstore as vectorstore
import prefect_data_getters.utilities.constants as C
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from prefect_data_getters.stores.documents import _AIDocument, SlackMessageDocument, convert_documents_to_ai_documents
from typing import List
from typing import List, Literal, Optional, Annotated
from datetime import datetime
from langchain_elasticsearch.vectorstores import _hits_to_docs_scores


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
                store:ElasticsearchStore = store_info["store"]
                temp_results = store.similarity_search_by_vector_with_relevance_scores(qemb, top_k, filter=es_filter, num_candidates=10*top_k)
                temp_results_d = [d[0] for d in temp_results]
                docs = convert_documents_to_ai_documents(temp_results_d, store._store.index)
                if("slack" in store_info["name"]):
                    docs = extend_slack_messages(docs)
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
    


    def search_by_username(
        self,
        index: str,
        username: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search documents in Elasticsearch by username, time range, and metadata filter.

        Args:
            username (str): The username to search for.
            from_date (datetime, optional): Start date for the range filter. Defaults to None.
            to_date (datetime, optional): End date for the range filter. Defaults to None.
            metadata_filter (dict, optional): Metadata filters as key-value pairs. Defaults to None.
            index (str, optional): Elasticsearch index to search. Defaults to '_all'.
            size (int, optional): Number of results to return. Defaults to 10.

        Returns:
            List[Dict[str, Any]]: List of documents matching the query.
        """

        selected_store = [store for store in self.stores if store["name"] == index][0]
        # Base search query
        es = Elasticsearch("http://localhost:9200")
        s = Search(using=es, index=selected_store["name"])

        if(index=="email_messages"):
            s = s.query("match", **{"metadata.from": username})
        elif(index=="jira_issues"):
            s = s.query("match", **{"metadata.assignee_displayName": username})
        elif(index=="slack_messages"):
            #TODO: add in a search for the user name in any slack mention
            # Also todo, take the output contexts and merge so there are not a bunch of repeats.
            s = s.query("match", **{"metadata.user": username})
        elif(index=="slab_documents" or index=="slab_document_chunks"):
            s = s.query("match", **{"metadata.owner": username})
        elif(index=="bitbucket_pull_requests"):
            s = s.query("match", **{"metadata.all_participants": username})
        else:
            raise Exception(f"user search not available for {index}")


        # Add date range filter
        if from_date or to_date:
            date_range = {}
            if from_date:
                date_range["gte"] = from_date.isoformat()
            if to_date:
                date_range["lte"] = to_date.isoformat()
            if("slack" in index):
                s = s.filter("range", metadata__ts_iso=date_range)
            else:
                s = s.filter("range", post_datetime=date_range)


        # Add metadata filters
        if metadata_filter:
            for key, value in metadata_filter.items():
                s = s.filter("term", **{f"metadata.{key}": value})

        # Sort by post_datetime ascending
        s = s.sort("post_datetime")

        # Limit the number of results
        s = s[:size]


        # Execute the search
        response = s.execute()
        # Parse and return the results
        results = [
            Document(page_content=hit.text, metadata=dict(hit.metadata), id=hit.meta.id)
            for hit in response
        ]
        docs = convert_documents_to_ai_documents(results, selected_store["name"])
        if("slack" in index):
            docs = extend_slack_messages(docs)
        return docs
    


from datetime import datetime, timedelta
from collections import defaultdict
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

def extend_slack_messages(
    slack_messages: list[SlackMessageDocument],
    minutes_before_after: int = 120
) -> list[SlackMessageDocument]:
    """
    Process a list of SlackMessageDocuments by:
    1. Deduplicating by thread_ts (if present) or by ts if not.
    2. For threads: produce one representative message (we already have one after dedup).
    3. For non-thread messages: 
       - Merge overlapping time windows.
       - Choose one representative message per channel window.
       - Extend only that representative message for the window.

    Args:
        slack_messages (list[SlackMessageDocument]): The original Slack messages.
        minutes_before_after (int): The time range in minutes before and after each message's timestamp.

    Returns:
        list[SlackMessageDocument]: The updated Slack message documents.
    """

    # Deduplicate by thread_ts if present, otherwise by ts
    dedup_map = {}
    for msg in slack_messages:
        ts_thread = msg._get_metadata("thread_ts")
        ts = msg._get_metadata("ts")
        channel = msg._get_metadata("channel")

        if not channel or not ts:
            continue  # skip if missing crucial metadata

        key = (channel, ts_thread if ts_thread else ts)
        if key not in dedup_map:
            dedup_map[key] = msg
        # If duplicate found, we ignore it since we only need one representative

    unique_messages = list(dedup_map.values())

    # Separate messages that have a thread_ts from those that do not
    thread_messages = []
    non_thread_messages = []
    for msg in unique_messages:
        if msg._get_metadata("thread_ts"):
            thread_messages.append(msg)
        else:
            non_thread_messages.append(msg)

    # For thread messages, we just take them as is since each represents a unique thread
    # and we have only one representative per thread.

    # For non-thread messages, we merge overlapping intervals per channel.
    channel_time_intervals = defaultdict(list)
    non_thread_data = []  # keep track of (channel, ts_datetime, msg) for interval assignment

    for msg in non_thread_messages:
        ts = float(msg._get_metadata("ts"))
        channel = msg._get_metadata("channel")
        if not channel:
            continue
        ts_datetime = datetime.utcfromtimestamp(ts)
        from_time = ts_datetime - timedelta(minutes=minutes_before_after)
        to_time = ts_datetime + timedelta(minutes=minutes_before_after)
        channel_time_intervals[channel].append((from_time, to_time))
        non_thread_data.append((channel, ts_datetime, msg))

    # Merge overlapping intervals for each channel
    for channel in channel_time_intervals:
        intervals = channel_time_intervals[channel]
        intervals.sort(key=lambda x: x[0])  # sort by start time
        merged = []
        current_start, current_end = intervals[0]

        for i in range(1, len(intervals)):
            start, end = intervals[i]
            if start <= current_end:
                # Overlapping interval
                current_end = max(current_end, end)
            else:
                # No overlap, push the previous interval and move on
                merged.append((current_start, current_end))
                current_start, current_end = start, end
        # Add the last interval
        merged.append((current_start, current_end))
        channel_time_intervals[channel] = merged

    # Now we have merged intervals. For each merged interval, pick one representative message.
    # We'll find which messages fall into each interval and choose the earliest by timestamp.
    representative_non_thread_messages = []

    # Map each interval to the messages that fall within it
    for channel, ts_datetime, msg in non_thread_data:
        for (start, end) in channel_time_intervals[channel]:
            if start <= ts_datetime <= end:
                representative_non_thread_messages.append((channel, start, end, ts_datetime, msg))
                break

    # Now we have a list of (channel, start, end, ts_datetime, msg).
    # Group by (channel, start, end) to pick one representative
    interval_groups = defaultdict(list)
    for channel, start, end, ts_datetime, msg in representative_non_thread_messages:
        interval_groups[(channel, start, end)].append((ts_datetime, msg))

    # For each interval group, pick the earliest message
    final_non_thread_representatives = []
    for key, msg_list in interval_groups.items():
        # Sort by ts_datetime to get the earliest message
        msg_list.sort(key=lambda x: x[0])
        earliest_msg = msg_list[0][1]  # earliest message by timestamp
        # key = (channel, start, end)
        start, end = key[1], key[2]
        # We'll run _extend_slack_message on this earliest_msg using the interval times
        final_non_thread_representatives.append((earliest_msg, start, end))

    # Extend all representative messages now
    extended_messages = []

    # Extend thread representatives
    for msg in thread_messages:
        extended = _extend_slack_message(slack_message=msg, from_time=None, to_time=None)
        extended_messages.append(extended)

    # Extend non-thread interval representatives
    for (msg, from_time, to_time) in final_non_thread_representatives:
        extended = _extend_slack_message(slack_message=msg, from_time=from_time, to_time=to_time)
        extended_messages.append(extended)

    return extended_messages


def _extend_slack_message(
    slack_message: SlackMessageDocument, 
    from_time: datetime = None, 
    to_time: datetime = None
) -> SlackMessageDocument:
    """
    Internal function to extend a Slack message by retrieving related context messages from the same channel.
    If it's part of a thread, retrieves all messages from the thread.
    If not, retrieves messages within the specified time range.

    Args:
        slack_message (SlackMessageDocument): The original Slack message document.
        from_time (datetime): Start of the time range (for non-thread messages).
        to_time (datetime): End of the time range (for non-thread messages).

    Returns:
        SlackMessageDocument: The updated Slack message document with extended context.
    """
    es_client = Elasticsearch(C.ES_URL)  # Initialize Elasticsearch client

    ts = slack_message._get_metadata("ts")
    ts_thread = slack_message._get_metadata("thread_ts")
    channel = slack_message._get_metadata("channel")

    if not ts or not channel:
        raise ValueError("Missing 'ts' or 'channel' metadata in the Slack message document.")

    if ts_thread:
        # Retrieve entire thread
        search_query = Search(using=es_client, index="slack_messages").query(
            "bool",
            must=[
                {"term": {"metadata.channel.keyword": channel}},
                {"term": {"metadata.thread_ts": str(ts_thread)}},
            ],
        ).sort("metadata.ts")
    else:
        # Use provided from_time and to_time
        if not from_time or not to_time:
            # fallback if missing
            ts_datetime = datetime.utcfromtimestamp(float(ts))
            from_time = ts_datetime - timedelta(minutes=120)
            to_time = ts_datetime + timedelta(minutes=120)

        search_query = Search(using=es_client, index="slack_messages").query(
            "bool",
            must=[
                {"term": {"metadata.channel.keyword": channel}},
                {
                    "range": {
                        "metadata.ts_iso": {
                            "gte": from_time,
                            "lte": to_time,
                        }
                    }
                },
            ],
        ).sort("metadata.ts")

    response = search_query.execute()

    context_messages = [
        f"[{datetime.fromtimestamp(float(msg.metadata['ts']))}] "
        f"{msg.metadata['user'] if 'user' in msg.metadata else 'NoName'}: {msg.text}"
        for msg in response.hits
    ]

    slack_message.set_page_content("\n".join(context_messages))
    return slack_message
