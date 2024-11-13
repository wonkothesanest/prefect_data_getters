import bs4
from langchain.tools.retriever import create_retriever_tool
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessageChunk, ToolMessageChunk, ToolMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
import chainlit as cl
from langchain.agents import AgentType
from langchain import hub
import stores.vectorstore as vs
from langchain_core.documents.base import Document


prompt = hub.pull("hwchase17/react-chat")



memory = MemorySaver()
llm = ChatOllama(model = "llama3.2", temperature = 0.0,)
# llm = ChatOpenAI(model="gpt-4o", temperature=0)

embeddings_model = vs.get_embeddings()
slack_vecstore = vs.get_slack()
slab_vecstore = vs.get_slab()

slab_ret = slab_vecstore.as_retriever(search_kwargs={'k': 20})
slack_ret = slack_vecstore.as_retriever(search_kwargs={'k': 20})


### Build retriever tool ###

slab_tool = create_retriever_tool(
    slab_ret,
    "slab_documents_retriever",
    "Searches and returns excerpts from Omnidian's technical and operational documentation.  This search is done via a vector store.",
)
slack_tool = create_retriever_tool(
    slack_ret,
    "slack_messages_retriever",
    "Searches and returns messages from an archive of all of Omnidian's slack messages.  Including private messages with me. This search is done via a vector store.",
)

# Duck Duck Go Search
ddg_search = DuckDuckGoSearchRun(api_wrapper=DuckDuckGoSearchAPIWrapper(safesearch="off", max_results=5))



tools = [slab_tool, slack_tool, ddg_search]

system_message = "You are a helpful assisstant. I am the user, my name is Dusty and i am an engineering manager at a Solar O&M provider called Omnidian.  Omnidian is a tech enabled company that allows us to monitor thousands of solar systems in both residential and commercial spaces to detect when things go wrong with them.  My teams include software engineering teams for acquiring external data from Omnidian (like solar OEMs and the data they provide, external simulations, weather data and anything else that might be helpful for detecting problems with solar systems or enabling us to service them better). I also manage an Onboarding team which enables our clients to give us their information about their assets as well as onboard their systems into our platforms.  My last team is called the client engagement team which develops tools that allow us to engage withour larger clients.  We give them summaries of their data and fleets of solar assets."
agent_executor = create_react_agent(
    llm, 
    tools, 
    state_modifier=SystemMessage(content=system_message),  
    checkpointer=memory,
    debug=True,
    )

config = {"configurable": {"thread_id": "abc123"}}


@cl.on_message  # This function is called for each user message
async def main(message: cl.Message):
    """
    Handle user message and stream tokens as they are received.
    Also, display tool input and output when the agent uses tools.
    """
    msg = cl.Message(content="test", author="Agent")  # Create a Chainlit message for streaming
    msgToolCall = cl.Message(content="", author="Tool Call")
    msgTool = cl.Message(content="", author="Tool")
    msgAgent = cl.Message(content="")
    # await msg.send()

    # Stream tokens and tool input/output
    for c in agent_executor.stream({"messages": [HumanMessage(content=message.content)]}, config=config, debug=False, stream_mode="messages"):
        for m in c:
            mtype = type(m)
            if(mtype==AIMessageChunk and m.tool_call_chunks):
                part = ""
                s = set()
                for p in m.tool_call_chunks:
                    part += p["args"]
                    s.add(p["name"])
                if(msgToolCall.content == ""):
                    part = f"{", ".join(s)}: {part}"
                await msgToolCall.stream_token(part)
                await msgToolCall.update()
            elif(mtype==AIMessageChunk and m.content):
                await msgAgent.stream_token(m.content)
                await msgAgent.update()
            elif(mtype==ToolMessage):
                msgTool.content = m.content
                await msgTool.send()
            if 'agent' in m:
                for mm in m['agent']["messages"]:
                    if(mm.tool_calls):
                        for t in mm.tool_calls:
                            await cl.Message(author="Tool Call", content=f"{t["name"]}: {t["args"]}").send()
                    else:
                        await cl.Message(author="Agent", content=f"{mm.content}").send()

            # Check if the agent used a tool
            if 'tools' in m:
                for t in m["tools"]["messages"]:
                    await cl.Message(author="Tool", content=t.content).send()

    await msg.update()  
