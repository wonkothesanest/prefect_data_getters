

from datetime import datetime, timedelta
from typing import Annotated, Any, List

from stores.documents import _AIDocument
from stores.vectorstore import ESVectorStore
from utilities.constants import VECTOR_STORE_NAMES, data_stores
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
import agents.report_template_okrs as OKR
import agents.reporting as P



from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage
import json
import asyncio
from collections import defaultdict
import utilities.constants as C
from concurrent.futures import ThreadPoolExecutor, as_completed
from utilities.people import HYPERION,person

from utilities.timing import print_human_readable_delta, time_it
# The agent state is the input to each node in the graph
class ReportState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    documents: List[_AIDocument]
    report_message: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    research: str
    report: str
    report_history: Annotated[List[str], operator.add]

# Initialize LLMs
json_llm = ChatOllama(model="llama3.1", format="json")
llm = ChatOpenAI(model="gpt-4o")
#llm = ChatOllama(model="llama3.1", num_ctx=120000)
doc_reviewer_llm = ChatOllama(model="llama3.1", num_ctx=120000)


searcher = MultiSourceSearcher()

# ====== FUNCTIONS ======
"""
Linear flow
    get documents
        get jira
        get emails
        get documentation
        get slack messages with context
    Write report to template for each section
    review and finalize report for each section
    combine the entire report from the sections
    print report

"""
@time_it
def run_report(docs: list[_AIDocument], report_message: str) -> str:
    # Setup state
    state = ReportState()
    state["documents"] = docs
    state["report_message"] = report_message
    state["messages"] = []

    # ====== WORKFLOW GRAPH ======

    workflow = StateGraph(ReportState)
    workflow.add_node("DocumentFormatter", document_formatter)
    workflow.add_node("Summarizer", document_summarizer)
    workflow.add_node("ReportWriter", report_writer)
    workflow.add_node("Reviewer", reviewer)

    workflow.add_edge(START, "DocumentFormatter")
    workflow.add_edge("DocumentFormatter", "Summarizer")
    workflow.add_edge("Summarizer", "ReportWriter")
    workflow.add_edge("ReportWriter", "Reviewer")
    workflow.add_conditional_edges("Reviewer", node_after_reviewer)

    graph = workflow.compile(debug=False)

    all_events = []
    for event in graph.stream(state, stream_mode="values"):
        all_events.append(event)
        if(event.get("report", None)):
            report = event.get('report')
        if(event.get('messages', False)):
            #event['messages'][-1].pretty_print()
            pass
    return report

def write_reports(all_reports: list, report_title: str):

    # print(all_events)

    # Create a timestamp
    report_title_f = report_title.lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"reporting_{report_title_f}_{timestamp}.md"

    # Open the file in write mode and write the reports
    with open(file_name, "w") as file:
        file.write(f"{report_title}\n\n")
        for r in all_reports:
            file.write(f"{r}\n=============\n")

#################### NODES ##########################
def _format_research(all_docs: list):
    r = ""
    for d in all_docs:
        r += f"\n{str(d)}\n"
    return r

def document_formatter(state: ReportState):
    r = _format_research(state["documents"])
    return {
            'research': r
            }

def document_summarizer(state: ReportState):
    docs = state['documents']
    all_docs = []
    batch_size = 1  # Number of parallel requests
    llm_results = []

    def process_document(d: _AIDocument):
        """Process a single document with the LLM."""
        if(len(str(d)) > C.DESIRED_DOCUMENT_CHARACTER_LENGTH):
            p = P.summarization_prompt(
                str(d),
                f"I need bulletted highlights of all the key points of this document. Respond with only pertinent information and do not talk about reviewing documents"
            )
            r = (p | doc_reviewer_llm).invoke({})
        else:
            r = d.page_content
        return d, r

    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [executor.submit(process_document, d) for d in docs]

        for future in as_completed(futures):
            try:
                d, r = future.result()
                
                content_to_use = r if isinstance(r, str) else r.content

                if "OMIT" not in content_to_use:
                    if len(content_to_use) + len(d.page_content) <= C.DESIRED_DOCUMENT_CHARACTER_LENGTH:
                        content = f"{d.page_content}\nSummary: {content_to_use}"
                    else:
                        content = content_to_use
                    
                    d.set_page_content(content)
                    all_docs.append(d)
            except Exception as e:
                print(f"Error processing document: {e}")

    return {'documents': all_docs, 'research': _format_research(all_docs)}



def report_writer(state: ReportState):
    query = state["report_message"]
    prompt = P.report_prompt(query, 
                             state['research'], 
                             state.get("report_history", None)[-1] if state["report_history"] else "")
    result = (prompt | llm).invoke(state)
    return {
        "report": result.content, 
        "messages": [AIMessage(content=result.content)],
        "report_history": [result.content]
        }

def reviewer(state: ReportState):
    prompt = P.review_prompt(state['report'])
    review = (prompt | llm).invoke(state)
    if "FINISHED" not in review.content:
        is_finished = llm.invoke([SystemMessage(
            content="Reply 'YES' if the draft is good enough for delivery. Reply 'NO' otherwise."
        ), HumanMessage(content=review.content)])
    else:
        is_finished = True
    
    return {
        "is_finished": (is_finished == True or "yes" in is_finished.content.lower()),
        "report_history": [review.content],
        "messages": [AIMessage(content=review.content)]
    }

def node_after_reviewer(state: ReportState):
    return END if state.get("is_finished", False) else "ReportWriter"
