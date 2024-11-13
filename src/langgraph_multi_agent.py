from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from typing import Annotated, List, Dict
from stores.vectorstore import get_embeddings, get_slab, get_slack
from langchain_ollama import ChatOllama
from langchain_core.documents.base import Document
import json


# Initialize the vector store (Chroma)
chroma_store = get_slab()


# Base LLM setup
# llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
# llm = ChatOllama(model = "llama3.1:8b", temperature = 0.0,num_ctx=120000)
# llm = ChatOllama(model = "llama3.2:1b", temperature = 0.0,num_ctx=120000)
llm = ChatOllama(model = "llama3.2:3b", temperature = 0.0, num_ctx=120000)
# llm = ChatOllama(model = "phi3.5", temperature = 0.0,num_ctx=4000)


# Define state
class AgentState(TypedDict):
    prompt: str
    refined_query: str
    documents: List[Document]
    useful_documents: List[Document]
    answer: str

# Key term agent (node) to refine the query
def key_term_node(state: AgentState):
    refined_prompt = ChatPromptTemplate.from_template(
        # "List the key terms from the prompt: {prompt}. "
        "Here is the user's prompt: {prompt}"
        "Rephrase the prompt to be an input string that closely aligns with the intent of the prompt."
        "This input string will be used to find documents in a vector database. Include additional related information to better make the prompt align with a vector database search"
        "Only return the refined prompt. Do not add any explanatory information, only what should be entered into search."
    ).format_prompt(prompt=state["prompt"])
    response = llm.invoke(refined_prompt)
    state["refined_query"] = response.content
    print(f"The refined Query is: {response.content}")
    return state

# Document retrieval agent (node) to query the vector store
def retrieval_node(state: AgentState):
    documents = chroma_store.search(state["refined_query"],search_type="similarity" , k=20)  # Retrieve top 20 docs
    state["documents"] = documents #get_unique_docs(documents)
    print(f"returned {len(documents)} documents")
    return state

# summarizes each document into a synopsis that has to do with the prompt
def summarization_node(state:AgentState):
    pass

# Document evaluator agent (node) to filter out irrelevant documents
def evaluation_node(state: AgentState):
    useful_docs = []
    for doc in state["documents"]:
        evaluation_prompt = ChatPromptTemplate.from_template(
            "You are a document evaluation expert and can understand when documents are useful for answering questions and providing background for reasearch on a topic. "
            "Your job is to evaluate the given document for input to a query or a research subject provided below. "
            "Only reject documents that have nothing to do with the user ask. Accept documents that have key words or terms that might pertain to the query at hand but the document its self may not directly answer the question. "
            "Evaluate if the following document is useful: \n"
            "###################################\n"
            "{doc}"
            "###################################\n"
            "Was this document useful to help provide context to answer this query: {query}? \n"
            "Does it relate to the above or does the document have anything to do with: {query2} \n"
            "Respond with 'Accept' if the document was at least partially useful or 'Reject' if not. "
            "Respond with only one word.\n"
        ).format_prompt(doc=format_documents([doc]), query=state["prompt"], query2=state["refined_query"]).to_string()
        # print(evaluation_prompt)
        response = llm.invoke(evaluation_prompt)
        if "Accept" in response.content:
            useful_docs.append(doc)
        print(f"The evaluation was {response.content} for document [[{doc.metadata["title"]}]] \n")
    state["useful_documents"] = useful_docs
    return state

def answer_question(state: AgentState):
    print(f"Using {len(state["useful_documents"])} document(s) to answer {state["prompt"]}\n\n")
    prompt = ChatPromptTemplate.from_template(
        "With the following documents you should answer the initial question from the user.\n "
        "The documents which have been verified as being useful for answering the question: {docs} \n "
        "Using the context and information above answer this initial query from the user: {question} \n "
        "Answer to question: "
    ).format_prompt(docs=format_documents(state["useful_documents"]), question=state["prompt"]).to_string()
    response = llm.invoke(prompt)
    state["answer"] = response
    return state

def get_unique_docs(docs: list[Document]) -> list[Document]:
    return list({d.metadata["id"]: d for d in docs}.values())

def format_documents(docs: list[Document]) -> str:
    output = ""
    #unique_docs = get_unique_docs(docs)
    for d in docs:
        try: d.metadata.pop("document_content")
        except: pass
        
        output += f"""
Document Metadata:
{json.dumps(d.metadata)}

Document Content:
{d.page_content}

END Document
##########################################
"""
    return output

# Define the graph
workflow = StateGraph(AgentState)

# Adding nodes to the graph
workflow.add_node("KeyTermAgent", key_term_node)
workflow.add_node("RetrievalAgent", retrieval_node)
workflow.add_node("EvaluationAgent", evaluation_node)
workflow.add_node("AnswerAgent", answer_question)

# Define edges to control the flow
workflow.add_edge(START, "KeyTermAgent")
workflow.add_edge("KeyTermAgent", "RetrievalAgent")
workflow.add_edge("RetrievalAgent", "EvaluationAgent")
workflow.add_edge("EvaluationAgent", "AnswerAgent")
workflow.add_edge("AnswerAgent", END)

# Compile the graph
graph = workflow.compile()

# Run the system with a sample prompt
prompt = "What projects are we working on for everbright?"
initial_state = {"prompt": prompt, "refined_query": "", "documents": [], "useful_documents": []}

i = 0
for output in graph.stream(initial_state):
    last_output = output
    i += 1
    # print(output)


print(last_output['AnswerAgent']['answer'].content)
