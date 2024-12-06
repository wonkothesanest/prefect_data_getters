from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage

def query_prompt(input_query: str) -> ChatPromptTemplate:
    """Prompt to generate a vector database query and filter keywords."""
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "Your job is to create a query for a vector database that will generate the best information to retrieve data for a user query. "
            "You also supply filter keywords if you determine there may be phrases or words that documents must have one of. "
            "You only respond in JSON. The format of the JSON must be in the form of {\"search_queries\": [str], \"keywords\": [str]}. "
            "Do not add additional content."
        )),
        HumanMessage(content=f'"{input_query}" Rephrase the preceding querying into a short representative string.')
    ])

def summarization_prompt(documents: str, input_query: str) -> str:
    """Prompt to summarize a collection of documents."""
    return ChatPromptTemplate.from_messages([
        SystemMessage(content="You are a helpful assisstent that summarizes single or multiple batches of documents. "
                      " It is important to pay attention to the input query as you need to summarize the document "
                      "with all the pertinate information to helping to understand the input query better. "
                      " If the document(s) do not appear to be very relevant to the input query then "
                      " respond with only the word \"OMIT\" and do not add anything else in your response. "
                      " Do not respond with a summary of why you skipped the document. "
                      "Your response format should be in the form of a bulletted list with all the information that relates to the input query. "
                      "Your response should not contain any reference to the act of summarizing the document. "
                      ),
        HumanMessage(
        f"Take the following set of documents and summarize them based on their relevance to the input query: {input_query}. "
        f"Summarize each document or omit irrelevant ones. \nDocuments:\n\n{documents}"
    )])

def report_prompt(input_query: str, research_content: str, review_notes: str = None) -> ChatPromptTemplate:
    """Prompt to create a well-structured report based on research content."""
    additional_notes = f" Review Comments: {review_notes}" if review_notes else ""
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "You are a writer. Your job is to return a well-structured response to the user's query based on the research provided. "
            "Do not embellish or invent facts."
        )),
        MessagesPlaceholder(variable_name="messages"),
        HumanMessage(content=(f"Research and Supporting Documents: \n{research_content}")),
        HumanMessage(content=(
            f"Input Query: {input_query}\n{additional_notes}\n"
        ))
    ])

def review_prompt(draft: str) -> ChatPromptTemplate:
    """Prompt to review the report draft and provide feedback."""
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "You are a reviewer. Please review the latest draft and provide feedback focused on formatting and readability. "
            "Do NOT suggest adding more content. Reply 'FINISHED' if the draft is ready."
        )),
        MessagesPlaceholder(variable_name="messages"),
        HumanMessage(content=f"Draft to review:\n{draft}")
    ])
