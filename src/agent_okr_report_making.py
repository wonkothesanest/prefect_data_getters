

from datetime import datetime, timedelta
from typing import Annotated, Any, List

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

from utilities.timing import print_human_readable_delta
# The agent state is the input to each node in the graph
class AgentState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    messages: Annotated[Sequence[BaseMessage], operator.add]
    template: str
    okr: OKR.okr
    research: str
    documents: List[_AIDocument]
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

#################### NODES ##########################
def _format_research(all_docs: list):
    r = ""
    for d in all_docs:
        r += f"\n{str(d)}\n"
    return r

def get_documents(state: AgentState):
    okr = state["okr"]
    query_prompt = P.query_prompt(f"Find me information on the following OKR: {state["okr"].title}, {state['okr'].description}")
    query_result = (query_prompt| json_llm).invoke(state)
    query_result = json.loads(query_result.content)
    llm_reduction = False
    jiras = asyncio.run(searcher.search(
        query=query_result["search_queries"][0],
        top_k=50,
        keywords = None,
        from_date = datetime.now() - timedelta(weeks=12),
        indexes = ['jira_issues'],
        metadata_filter = {"project_key": okr.team},
        run_llm_reduction = llm_reduction
    ))

    slabs = asyncio.run(searcher.search(
        query=query_result["search_queries"][0],
        top_k=5,
        keywords = query_result.get("keywords", None),
        #from_date = datetime.now() - timedelta(weeks=2),
        indexes = ['slab_documents'],
        run_llm_reduction = llm_reduction
    ))
    emails = asyncio.run(searcher.search(
        query=query_result["search_queries"][0],
        top_k=10,
        keywords = None,
        from_date = datetime.now() - timedelta(weeks=12),
        indexes = ['email_messages'],
        run_llm_reduction = llm_reduction
    ))
    slacks = asyncio.run(searcher.search(
        query=query_result["search_queries"][0],
        top_k=10,
        keywords = None,
        indexes = ['slack_messages'],
        run_llm_reduction = llm_reduction
    ))
    all_docs =  slabs + jiras + emails + slacks

    r = _format_research(all_docs)
    return {'documents': all_docs,
            'research': r
            }

def document_summarizer(state: AgentState):
    docs = state['documents']
    all_docs = []
    batch_size = 5  # Number of parallel requests
    llm_results = []

    def process_document(d: _AIDocument):
        """Process a single document with the LLM."""
        if(len(str(d)) > C.DESIRED_DOCUMENT_CHARACTER_LENGTH):
            p = P.summarization_prompt(
                str(d),
                f"I need bulletted highlights of all the key points of this document in the context of the following OKR to be performed by the {state['okr'].team}. OKR: {state['okr'].title} {state['okr'].description}. Respond with only pertinent information and do not talk about reviewing documents"
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



def report_writer(state: AgentState):
    okr = state["okr"]
    query = f"""
I need a report to be written about an OKR. Here is some information about the OKR for my {okr.team} team.
Title: {okr.title}
Description: {okr.description}

The short report should have the following sections to it
* Status
* Progress
* Next Steps
* Blockers

Status can be In Progress, Done, At Risk or Postponed

You should use the documents below, especially the JIRA ones to pull together a cohesive summary of work done recently and what is next.
Here is an example of the output I would like to see:

EXAMPLE: 

## KR 1.1: An example title of a KR
### Status: AT RISK
### Progress:
* Brief description of what is in progress.
* Another item
### Next Steps:
* Items that are next up to be done
### New Risks:
* Any Risks identified
### Blockers:
* None.

### Backup Documentation
* Have a list of documents that back up your report
* List them out in this section.

"""
    prompt = P.report_prompt(query, 
                             state['research'], 
                             state.get("report_history", None)[-1] if state["report_history"] else "")
    result = (prompt | llm).invoke(state)
    return {
        "report": result.content, 
        "messages": [AIMessage(content=result.content)],
        "report_history": [result.content]
        }

def reviewer(state: AgentState):
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

def node_after_reviewer(state: AgentState):
    return END if state.get("is_finished", False) else "ReportWriter"



# ====== WORKFLOW GRAPH ======

workflow = StateGraph(AgentState)
workflow.add_node("Researcher", get_documents)
workflow.add_node("ReportWriter", report_writer)
workflow.add_node("Reviewer", reviewer)
workflow.add_node("Summarizer", document_summarizer)

workflow.add_edge(START, "Researcher")
workflow.add_edge("Researcher", "Summarizer")
workflow.add_edge("Summarizer", "ReportWriter")
# workflow.add_edge("Researcher", "ReportWriter")
workflow.add_edge("ReportWriter", "Reviewer")
workflow.add_conditional_edges("Reviewer", node_after_reviewer)

graph = workflow.compile(debug=False)

all_events = []
all_reports = []
for okr in OKR.okrs_2024_q4:
    start_time = datetime.now()
    report = None
    for event in graph.stream({"messages": [], "okr": okr}, stream_mode="values"):
        all_events.append(event)
        if(event.get("report", None)):
            report = event.get('report')
        if(event.get('messages', False)):
            #event['messages'][-1].pretty_print()
            pass
    print("Final Report: ")
    print(str(okr))
    print(report)
    print(f"END {str(okr.title)}")
    end_time = datetime.now()
    print_human_readable_delta(start_time, end_time)
    all_reports.append({"okr": str(okr), "report": report})
    print("===================")

# print(all_events)

for r in all_reports:
    print(f"{r["okr"]}\n\n{r["report"]}\n=============\n")

# print(all_reports)
i=0
