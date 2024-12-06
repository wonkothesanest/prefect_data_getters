

from typing import Annotated, Any

from stores.documents import _AIDocument
from stores.vectorstore import ESVectorStore
from utilities.constants import data_stores
from langchain.schema import Document
from langchain_core.tools import tool
from langchain_core.output_parsers.json import JsonOutputParser
from langchain.chains.llm import LLMChain
from langchain_ollama.llms import OllamaLLM
# from langchain_ollama.chat_models import ChatOllama
from langchain_ollama import ChatOllama
from stores.rag_man import MultiSourceSearcher
import asyncio
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing import Literal

from typing import Annotated, Literal

import functools
import operator
from typing import Sequence
from typing_extensions import TypedDict
import json
from langchain_core.messages import BaseMessage, ChatMessage

from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import create_react_agent
from langchain_core.callbacks import StdOutCallbackHandler
import tools.search as searchers

from agents.reporting import (
    query_prompt,
    summarization_prompt,
    report_prompt,
    review_prompt
)

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage
import json
import asyncio


# The agent state is the input to each node in the graph
class AgentState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # The 'next' field indicates where to route to next
    next: Annotated[str, "A choice between one of the next agents to run"]
    input_query: str
    search_query: str
    search_keywords: str
    documents: list
    report_draft: str
    is_finished: bool
    review_notes: str

# Initialize LLMs
json_llm = ChatOllama(model="llama3.1", format="json")
llm = ChatOllama(model="llama3.1", num_ctx=120000)

searcher = MultiSourceSearcher()

# ====== FUNCTIONS ======

def query_agent(state):
    prompt = query_prompt(state["input_query"])
    result = (prompt | json_llm).invoke(state)
    data = json.loads(result.content)
    return {"search_queries": data["search_queries"], "search_keywords": data["keywords"]}

def search(query: str, keywords: list[str]) -> list:
    docs = asyncio.run(searcher.search(query, keywords=keywords, top_k=15))
    return docs

def research(state):
    all_docs = []
    for query in state["search_queries"]:
        docs = search(query, state["search_keywords"])
        all_docs.extend(docs)
    
    documents_content = "\n########################\n".join(map(str, all_docs))
    summarization = summarization_prompt(documents_content, state["input_query"])
    summary = llm.invoke([('system', summarization)])
    return {"documents": all_docs, "messages": [AIMessage(content=summary.content)]}

def report_writer(state):
    research_content = "\n\n".join([str(d) for d in state["documents"]])
    prompt = report_prompt(state["input_query"], research_content, state.get("review_notes"))
    result = (prompt | llm).invoke(state)
    return {"report_draft": result.content, "messages": [AIMessage(content=result.content)]}

def reviewer(state):
    prompt = review_prompt(state["report_draft"])
    review = (prompt | llm).invoke(state)
    
    is_finished = llm.invoke([SystemMessage(
        content="Reply 'YES' if the draft is ready for delivery. Reply 'NO' otherwise."
    ), HumanMessage(content=review.content)])
    
    return {
        "is_finished": "yes" in is_finished.content.lower(),
        "review_notes": review.content if "no" in is_finished.content.lower() else "",
        "messages": [AIMessage(content=review.content)]
    }

def from_rewriter(state):
    return END if state.get("is_finished", False) else "ReportWriter"

# ====== WORKFLOW GRAPH ======
researcher = create_react_agent(llm, [searchers.search_emails])

workflow = StateGraph(AgentState)
workflow.add_node(query_agent)
workflow.add_node("Researcher", researcher)
workflow.add_node("ReportWriter", report_writer)
workflow.add_node("Reviewer", reviewer)

workflow.add_edge(START, "query_agent")
workflow.add_edge("query_agent", "Researcher")
workflow.add_edge("Researcher", "ReportWriter")
workflow.add_edge("ReportWriter", "Reviewer")
workflow.add_conditional_edges("Reviewer", from_rewriter)

graph = workflow.compile(debug=False)

messages = [HumanMessage(content="What them.  Back up your statements by quoting from supplied documents. Try to ground your output in information collected and provided.")]

for event in graph.stream({"messages": messages,"input_query": messages[0].content}):
    for v in event.values():
        if(v.get('messages', False)):
             v['messages'][-1].pretty_print()

