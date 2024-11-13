from langchain_community.llms import OpenAI

# llm = OpenAI(model_name="gpt-3.5-turbo")
# response = llm("Hello, how are you?")
# print(response)
from openai import OpenAI

client = OpenAI()


import openai
from langchain.llms import OpenAI
from langchain.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from langchain.schema import Document

# Initialize OpenAI LLM
openai.api_key = "your-openai-api-key"

def initialize_chroma_store(persist_directory):
    """Initializes and loads the Chroma store."""
    return Chroma(persist_directory=persist_directory)

def query_chroma_vector_store(vectorstore, query, num_docs=20):
    """Queries the Chroma vector store for relevant documents."""
    return vectorstore.similarity_search(query, k=num_docs)

def prepare_document_text(documents):
    """Converts documents and their metadata into a format suitable for LLM processing."""
    document_texts = []
    for doc in documents:
        meta = doc.metadata
        content = f"Document: {doc.page_content}\nMetadata: {meta}\n\n"
        document_texts.append(content)
    return "\n".join(document_texts)

# Step 1: Query Vector DB Chain
def create_query_chain():
    query_prompt = PromptTemplate(
        input_variables=["query"],
        template="You need to query two local databases: Slack and Slab. Your query is: {query}. "
                 "Retrieve 20 relevant documents from each database."
    )
    return LLMChain(llm=OpenAI(model_name="gpt-4"), prompt=query_prompt)

# Step 2: Follow-up Query Decision Chain
def create_follow_up_chain():
    follow_up_prompt = PromptTemplate(
        input_variables=["documents", "query"],
        template="You have the following documents: {documents}. "
                 "Do you need to make a follow-up query to answer the question: {query}?"
    )
    return LLMChain(llm=OpenAI(model_name="gpt-4"), prompt=follow_up_prompt)

# Step 3: Final Answer Chain
def create_final_answer_chain():
    final_answer_prompt = PromptTemplate(
        input_variables=["documents", "query"],
        template="Based on the following documents: {documents}, please answer the question: {query}."
    )
    return LLMChain(llm=OpenAI(model_name="gpt-4"), prompt=final_answer_prompt)

# Main program
def main(query):
    # Initialize both Chroma vector stores for Slack and Slab
    slack_vectorstore = initialize_chroma_store("path/to/slack_vectorstore")
    slab_vectorstore = initialize_chroma_store("path/to/slab_vectorstore")

    # Query both vector stores for relevant documents
    slack_docs = query_chroma_vector_store(slack_vectorstore, query)
    slab_docs = query_chroma_vector_store(slab_vectorstore, query)

    # Combine documents from both sources
    all_documents = slack_docs + slab_docs
    doc_text = prepare_document_text(all_documents)

    # Create individual chains
    query_chain = create_query_chain()
    follow_up_chain = create_follow_up_chain()
    final_answer_chain = create_final_answer_chain()

    # Create a sequential chain
    sequential_chain = SequentialChain(
        chains=[query_chain, follow_up_chain, final_answer_chain],
        input_variables=["query"],
        output_variables=["final_answer"]
    )

    # Run the chain
    result = sequential_chain.run(query=query, documents=doc_text)
    print(f"Final answer: {result}")

if __name__ == "__main__":
    query = "What are the recent updates in the project?"
    main(query)
