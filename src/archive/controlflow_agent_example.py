import bs4
from langchain.tools.retriever import create_retriever_tool
from langchain.tools.requests.tool import RequestsGetTool
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
import controlflow as cf
import requests
from typing import Annotated


prompt = hub.pull("hwchase17/react-chat")

memory = MemorySaver()
llm = ChatOllama(model = "llama3.2", temperature = 0.0,)
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# llm=None

# cf.defaults.model = llm

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

@cf.tool(description="Get a web url's content from a requests.get call")
def get_tool(url: str) -> str:
    v = str(requests.get(url).content)
    print(v)
    return v[:500]

tools = [slab_tool, slack_tool, ddg_search]
import controlflow as cf
cf.settings.log_level = "DEBUG"
cf.settings.log_all_messages = True




# Agent 1: CrawlerAgent
CrawlerAgent = cf.Agent(
    model=llm,
    name="CrawlerAgent",
    description="Responsible for crawling the web page and retrieving the HTML and text content of the page, including linked pages one level deep.",
    instructions="Crawl the given URL, retrieve its content, and recursively visit all linked pages one level deep to gather text.",
    tools=[get_tool],
    interactive=False,
)
WebGetterAgent = cf.Agent(
    model=llm,
    name="WebGetterAgent",
    description="Responsible for getting the content of a web page and retrieving the HTML and text content of the page.",
    tools=[get_tool],
    interactive=False,
)

# Agent 2: LinkExtractorAgent
LinkExtractorAgent = cf.Agent(
    model=llm,
    name="LinkExtractorAgent",
    description="Extracts all internal links (URLs) from the HTML content of a page.",
    instructions="Analyze the HTML of the page and extract all internal links (URLs) for further crawling.",
    tools=[],
    interactive=False
)

# Agent 3: ContentParserAgent
ContentParserAgent = cf.Agent(
    model=llm,
    name="ContentParserAgent",
    description="Parses HTML into structured text format for further analysis.",
    instructions="Parse the retrieved HTML into clean, structured text for easier processing and analysis.",
    tools=[],
    interactive=False
)

# Agent 4: SummarizationAgent
SummarizationAgent = cf.Agent(
    model=llm,
    name="SummarizationAgent",
    description="Summarizes content to provide a concise overview of the main points on each page.",
    instructions="Generate concise summaries of the content from each page, capturing the key points.",
    tools=[],
    interactive=False
)

# Agent 5: KeyTermsAgent
KeyTermsAgent = cf.Agent(
    model=llm,
    name="KeyTermsAgent",
    description="Extracts key terms and topics from the text of each crawled page.",
    instructions="Analyze the content and extract important key terms and topics for indexing or analysis.",
    tools=[],
    interactive=False
)

# Agent 6: SentimentAnalysisAgent
SentimentAnalysisAgent = cf.Agent(
    model=llm,
    name="SentimentAnalysisAgent",
    description="Analyzes the sentiment (positive, negative, neutral) of the content from each page.",
    instructions="Analyze the sentiment of the text content to classify it as positive, negative, or neutral.",
    tools=[],
    interactive=False
)

# Agent 7: TopicClassificationAgent
TopicClassificationAgent = cf.Agent(
    model=llm,
    name="TopicClassificationAgent",
    description="Classifies the text into predefined categories such as 'Technical', 'Marketing', 'Educational', etc.",
    instructions="Classify the text content into the appropriate predefined categories for better understanding.",
    tools=[],
    interactive=False
)

# Agent 8: DependencyMappingAgent
DependencyMappingAgent = cf.Agent(
    model=llm,
    name="DependencyMappingAgent",
    description="Maps relationships and dependencies between the content of different crawled pages.",
    instructions="Analyze the links and map out the relationships or dependencies between the crawled pages' content.",
    tools=[],
    interactive=False
)

# Agent 9: TextValidationAgent
TextValidationAgent = cf.Agent(
    model=llm,
    name="TextValidationAgent",
    description="Validates the parsed text to ensure it's clean and usable for analysis.",
    instructions="Validate the parsed text to ensure it is clean, complete, and ready for further analysis.",
    tools=[],
    interactive=False
)

# Agent 10: AnomalyDetectionAgent
AnomalyDetectionAgent = cf.Agent(
    model=llm,
    name="AnomalyDetectionAgent",
    description="Detects anomalies in the text or structure of the crawled content, such as broken links or missing data.",
    instructions="Analyze the content and detect any anomalies or inconsistencies such as broken links, unexpected structures, or errors.",
    tools=[],
    interactive=False
)

# Agent 11: InsightsAgent
InsightsAgent = cf.Agent(
    model=llm,
    name="InsightsAgent",
    description="Generates insights based on the content and analyses to help solve the given task.",
    instructions="Combine the analyzed results and generate insights to help solve the task based on the webpage crawl.",
    tools=[],
    interactive=False
)

# Agent 12: ReportGeneratorAgent
ReportGeneratorAgent = cf.Agent(
    model=llm,
    name="ReportGeneratorAgent",
    description="Compiles all the findings and outputs from other agents into a comprehensive report.",
    instructions="Take all the findings from the other agents, including key terms, sentiment, and insights, and generate a final report summarizing the webpage analysis.",
    tools=[],
    interactive=False
)


import controlflow as cf

@cf.flow()
def WebpageCrawlFlow(url):
    agents = [
        WebGetterAgent,
        CrawlerAgent,
        LinkExtractorAgent,
        ContentParserAgent,
        SummarizationAgent,
        KeyTermsAgent,
        SentimentAnalysisAgent,
        TopicClassificationAgent,
        DependencyMappingAgent,
        TextValidationAgent,
        AnomalyDetectionAgent,
        InsightsAgent,
        ReportGeneratorAgent
    ]
    # tasks = cf.plan(objective="Write up a comprehensive documentation of all the python functions on the provided page", 
    #                 agents=agents, 
    #                 context={"url": "https://controlflow.ai/welcome"},
    #                 )
    # cf.run_tasks(tasks=tasks, max_llm_calls=20)
    # Step 1: Crawl the page and extract links
    html_content = cf.run("Get the content of an html page", agents=[WebGetterAgent], context=dict(url=url))
    
    # Step 2: Extract and validate links
    links = cf.run("Extract all the links from the given html content", agents=[LinkExtractorAgent], context=dict(html=html_content))
    
    # Step 3: Initialize storage for all parsed content
    parsed_content = {}
    
    for link in links:
        # Step 4: Parse content for each link
        content = cf.run("Parse content", agents=[ContentParserAgent], context=dict(link=link))
        parsed_content[link] = content
        
        # Step 5: Summarize content for each page
        summary = cf.run("Summarize content", agents=[SummarizationAgent], context=dict(content=content))
        
        # Step 6: Extract key terms and topics
        key_terms = cf.run("Extract key terms", agents=[KeyTermsAgent], context=dict(content=summary))
        
        # Step 7: Analyze sentiment
        sentiment = cf.run("Analyze sentiment", agents=[SentimentAnalysisAgent], context=dict(content=key_terms))
        
        # Step 8: Classify topics
        topic = cf.run("Classify topic", agents=[TopicClassificationAgent], context=dict(content=sentiment))
        
        # Step 9: Map content relationships between pages
        dependency_map = cf.run("Map dependencies", agents=[DependencyMappingAgent], context=dict(content=parsed_content))
        
        # Step 10: Add the result to the flow context
        # cf.add_to_flow_context(
        #     link=link, 
        #     summary=summary, 
        #     key_terms=key_terms, 
        #     sentiment=sentiment, 
        #     topic=topic, 
        #     dependency_map=dependency_map
        # )
    
    # Step 11: Detect anomalies in the data
    anomalies = cf.run("Detect anomalies", agents=[AnomalyDetectionAgent], context=parsed_content)
    
    # Step 12: Generate insights from the analyzed data
    insights = cf.run("Generate insights", agents=[InsightsAgent], context=parsed_content)
    
    # Step 13: Compile a final report with all the findings
    report = cf.run("Generate final report", agents=[ReportGeneratorAgent], context=dict(insights=insights, anomalies=anomalies))
    
    return report

# Execute the flow on a given URL
result = WebpageCrawlFlow(url="https://controlflow.ai/welcome")
print(result)
