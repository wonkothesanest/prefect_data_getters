import asyncio
from typing import List, Literal, Optional, Dict, Any
from langchain_elasticsearch import ElasticsearchStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.retrievers.document_compressors import LLMChainFilter
import stores.vectorstore as vectorstore
import utilities.constants as C
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from stores.documents import _AIDocument, convert_documents_to_ai_documents
from typing import List



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
        query: str, 
        top_k: int = 5, 
        keywords: Optional[List[str]] = None
    ) -> List[_AIDocument]:
        # Build keyword query for Elasticsearch, if keywords are provided
        keyword_filter = {
            "bool": {
                "should": [{"match": {"text": keyword}} for keyword in keywords],
                "minimum_should_match": 1,
            }
        } if keywords else None

        print("start")
        t1 = datetime.now()

        additional = await self.get_keywords_and_embeddings(query=query)
        # Use the LLM to select relevant data stores
        selected_stores = set(await self.select_stores(query))

        # Create tasks for similarity and keyword searches across each selected store
        search_results = []
        additional.embeddings.extend([query])
        for q in additional.embeddings:
            qemb = self.embeddings.embed_query(q)
            for store in selected_stores: #[s["store"] for s in self.stores]:
                temp_results = store.similarity_search_by_vector_with_relevance_scores(qemb, top_k, filter=keyword_filter)
                temp_results_d = [d[0] for d in temp_results]
                docs = convert_documents_to_ai_documents(temp_results_d, store._store.index)
                for i in range(len(temp_results)):
                    search_results.append((docs[i], temp_results[i][1]))
        # Run all search tasks concurrently and gather results
        # search_results = await asyncio.gather(*search_results)

        search_results.sort(key=lambda x: x[1], reverse=True)

        # Flatten the list of results
        # combined_results = [doc for result in search_results for doc in result]
        combined_results = [d[0] for d in search_results]
        combined_results = list({c.id: c for c in combined_results}.values())


        # Asynchronously filter results using the LLM
        # filtered_results = self.llm_filter.compress_documents(combined_results[:top_k], query)
        docs = []
        for d in combined_results:
            docs.extend(self.llm_filter.compress_documents([d], query))
            # print(len(docs))
            if(len(docs) >= top_k):
                break

        t2 = datetime.now()
        print(f"end: took {(t2-t1).seconds}")

        # Return sorted filtered results
        return docs
