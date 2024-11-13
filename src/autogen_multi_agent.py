from typing import Annotated, Literal

import os
import autogen
from autogen import ConversableAgent

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
from stores.documents import _AIDocument
from stores.vectorstore import ESVectorStore
from utilities.constants import data_stores
from langchain.schema import Document
from langchain_core.tools import tool
from langchain.chains.llm import LLMChain
from langchain_ollama.llms import OllamaLLM
from stores.rag_man import MultiSourceSearcher
import asyncio

llm = OllamaLLM(model="llama3.2")
searcher = MultiSourceSearcher()


docs = asyncio.run( 
    searcher.search(
        "what are the future plans for the data acquisition team?", 
        keywords=None,
        top_k=30)
        )

print(len(docs))
for d in docs:
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    print(d)
# @tool
# def search(query:Annotated[str, "Input query to generate several more vector search queries to query vector databases"],
#            keywords: Annotated[list[str], "List of keywords that the documents must have one of to be considered."]
#            ) -> list[_AIDocument]:
#     return searcher.search(query, keywords=keywords, top_k=30)
# from typing import Annotated, List
# from langchain.tools import tool
# from langchain_openai import ChatOpenAI
# from langgraph.graph import StateGraph, MessagesState, START

# # Define the search tool
# @tool
# def search(
#     query: Annotated[str, "Input query to generate several more vector search queries to query vector databases"],
#     keywords: Annotated[List[str], "List of keywords that the documents must have one of to be considered."]
# ) -> List[dict]:
#     # Implement your search logic here
#     # For demonstration, returning an empty list
#     return []

# from typing import Annotated, List
# from langchain import Agent, Tool, LLM
# from langchain.tools import tool
# from langchain.agents import initialize_agent

# # Define the search tool
# @tool
# def search(
#     query: Annotated[str, "Input query to generate several more vector search queries to query vector databases"],
#     keywords: Annotated[List[str], "List of keywords that the documents must have one of to be considered."]
# ) -> List[dict]:
#     # Implement your search logic here
#     # For demonstration, returning a mock result
#     return [{"title": "Sample Document", "content": "This is a sample document."}]

# # Define the agents
# class QueryGenerator(Agent):
#     def run(self, context):
#         # Generate queries based on the context
#         return "Generated query based on context."

# class Researcher(Agent):
#     def run(self, context):
#         # Use the search tool to perform research
#         results = search(query=context['query'], keywords=context['keywords'])
#         return results

# class ReportWriter(Agent):
#     def run(self, context):
#         # Compile a report based on the research results
#         return "Compiled report based on research results."

# class Reviewer(Agent):
#     def run(self, context):
#         # Review the report and provide feedback
#         return "Reviewed report with feedback."

# # Define the orchestrator
# class Orchestrator(Agent):
#     def __init__(self, llm: LLM):
#         self.llm = llm
#         self.agents = {
#             'QueryGenerator': QueryGenerator(),
#             'Researcher': Researcher(),
#             'ReportWriter': ReportWriter(),
#             'Reviewer': Reviewer()
#         }
#         self.context = {}

#     def run(self, initial_input):
#         self.context['initial_input'] = initial_input
#         next_agent = 'QueryGenerator'
#         while next_agent:
#             agent = self.agents[next_agent]
#             output = agent.run(self.context)
#             self.context[next_agent] = output
#             # Use LLM to decide the next agent
#             next_agent = self.decide_next_agent()
#             if next_agent == 'End':
#                 break
#         return self.context

#     def decide_next_agent(self):
#         # Use the LLM to decide the next agent based on the current context
#         # For demonstration, a simple decision logic is implemented
#         if 'QueryGenerator' not in self.context:
#             return 'QueryGenerator'
#         elif 'Researcher' not in self.context:
#             return 'Researcher'
#         elif 'ReportWriter' not in self.context:
#             return 'ReportWriter'
#         elif 'Reviewer' not in self.context:
#             return 'Reviewer'
#         else:
#             return 'End'

# # Initialize the orchestrator with an LLM
# llm = LLM()  # Replace with your LLM initialization
# orchestrator = Orchestrator(llm=llm)

# # Run the orchestrator with initial input
# initial_input = "Research topic: The impact of AI on healthcare."
# final_context = orchestrator.run(initial_input)
# print(final_context)
