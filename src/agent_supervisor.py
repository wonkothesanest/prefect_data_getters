

from typing import Annotated, Any

from stores.documents import _AIDocument
from stores.vectorstore import ESVectorStore
from utilities.constants import data_stores
from langchain.schema import Document
from langchain_core.tools import tool
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


class MyCallback(StdOutCallbackHandler):
    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        print(f"LLM started with prompts: {prompts}")

handler = MyCallback()

#llm = ChatOllama(model="llama3.1", format='json', callbacks=[handler])

llm = ChatOpenAI(model="gpt-4o")
searcher = MultiSourceSearcher()

class MyCallback(StdOutCallbackHandler):
    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        return super().on_llm_start(serialized,prompts, **kwargs)
    def on_llm_end(self, response, *, run_id, parent_run_id = None, **kwargs):
        return super().on_llm_end(response, run_id=run_id, parent_run_id=parent_run_id, **kwargs)
    


def agent_node(state, agent, name):
    result = agent.invoke(state)
    # print(f"{name}: \n{result["messages"][-1].content}\n\n-----------------------------\n\n")
    return {
        "messages": [HumanMessage(content=result["messages"][-1].content, name=name)]
    }


members = ["Researcher", "Reviewer", "ReportWriter"]
system_prompt = (
    "You are a supervisor tasked with managing a conversation between the"
    f" following workers:  {members}. Given the following user request,"
    " respond with the worker to act next. Each worker will perform a"
    " task and respond with their results and status. When finished,"
    " respond with {'next': 'FINISH'}. You must respond in JSON and only JSON "
    " Example response for choosing the reviewer to go next: {'next':'Reviewer'}"
)
# Our team supervisor is an LLM node. It just picks the next agent to process
# and decides when the work is completed
options = ["FINISH"] + members


class routeResponse(BaseModel):
    next: Annotated[Literal[*options], "The next agent to go."]
    reasoning: Annotated[str, "The reason you chose the actor in 'next'"]


prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        SystemMessage(
            content="Given the conversation above, who should act next? "
            "Make sure to give your answer with a next property. "
            "Return only a next value when choosing the next speaker "
            "Example: {'next':'Reviewer'} "
            f" Or should we FINISH? Select one of: {options}",
        ),
    ]
).partial(options=str(options), members=", ".join(members))


def supervisor_agent(state):
    supervisor_chain = (prompt | llm.with_structured_output(routeResponse) )
    # supervisor_chain = LLMChain(llm=llm, prompt=prompt, verbose=True)
    ret =  supervisor_chain.invoke(state)
    return ret


"""
This class should be able to search for relative documents,
Get a host of them, have an LLM parse out what is valuable research and what can be discarded.
Inputs: The original Task, a summary of what is being searched for, list of key words optional
Outputs: a list of documents that will help with the current question

Instantiate the vector stores when needed
Perform searches on the keywords, perform vector searches on the vec databases
Coallece documents by id.
async calls to LLMs to evaluate if a document is relevant to the task at hand
Rank all the remaining documents.
Return the top k documents desired.
"""

@tool
def search(query:Annotated[str, "Input query to generate several more vector search queries to query vector databases"],
           keywords: Annotated[list[str], "List of keywords that the documents must have one of to be considered."]
           ) -> list[_AIDocument]:
    """Search tool to search across multiple data sources including documentation, jira tickets, slack messages and email messages"""
    print(f"Received Query: {query} with keywords {keywords}")
    s = ""
    for d in asyncio.run( searcher.search(query, keywords=keywords, top_k=5)):
        s+=str(d)
    return s
@tool
def statusPrint(status: Annotated[str, "Status or brief message that the user should know"]):
    """Simply prints a message to the user"""
    print(status)



# The agent state is the input to each node in the graph
class AgentState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # The 'next' field indicates where to route to next
    next: Annotated[str, "A choice between one of the next agents to run"]


research_agent = create_react_agent(llm, tools=[search], debug=True)
research_node = functools.partial(agent_node, agent=research_agent, name="Researcher")

report_writer_agent = create_react_agent(llm, tools=[statusPrint], debug=False)
report_writer_node = functools.partial(agent_node, agent=report_writer_agent, name="ReportWriter")

# NOTE: THIS PERFORMS ARBITRARY CODE EXECUTION. PROCEED WITH CAUTION
reviewer_agent = create_react_agent(llm, tools=[statusPrint])
reviewer_node = functools.partial(agent_node, agent=reviewer_agent, name="Reviewer")

workflow = StateGraph(AgentState)
workflow.add_node("Researcher", research_node)
workflow.add_node("ReportWriter", report_writer_node)
workflow.add_node("Reviewer", reviewer_node)
workflow.add_node("supervisor", supervisor_agent)


# Now connect all the edges in the graph.

# In[5]:


for member in members:
    # We want our workers to ALWAYS "report back" to the supervisor when done
    workflow.add_edge(member, "supervisor")
# The supervisor populates the "next" field in the graph state
# which routes to a node or finishes
conditional_map = {k: k for k in members}
conditional_map["FINISH"] = END
workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
# Finally, add entrypoint
workflow.add_edge(START, "supervisor")

graph = workflow.compile(debug=False)



for s in graph.stream(
    {"messages": [HumanMessage(content="Write a brief research report on the future of data acquisition and their strategies for the future.")]},
    {"recursion_limit": 15},
):
    if "__end__" not in s:
        print(s)
        pass
        # print("----")
