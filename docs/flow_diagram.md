# Flow Diagram of Actions in the Prefect Data Getters System

## Overview

This diagram illustrates the data flow through the system, from data collection to reporting. The system is organized into several key components:

1. **Data Getters**: Collect data from various sources
2. **Exporters**: Process and format the collected data
3. **Enrichers**: Enhance the data with additional information
4. **Stores**: Store the processed data
5. **Management AI**: Generate reports and insights from the stored data

```mermaid
flowchart TD
    %% Main Components
    DG[Data Getters] --> EX[Exporters]
    EX --> EN[Enrichers]
    EN --> ST[Stores]
    ST --> MA[Management AI]
    
    %% Data Getters Subcomponents
    DG --> DG_SLACK[Slack Backup]
    DG --> DG_GMAIL[Gmail Backup]
    DG --> DG_JIRA[Jira Backup]
    DG --> DG_BITBUCKET[Bitbucket Backup]
    DG --> DG_SLAB[Slab Backup]
    DG --> DG_GCAL[Google Calendar Backup]
    
    %% Exporters Subcomponents
    EX --> EX_SLACK[Slack Exporter]
    EX --> EX_GMAIL[Gmail Exporter]
    EX --> EX_JIRA[Jira Exporter]
    EX --> EX_SLAB[Slab Exporter]
    EX --> EX_GCAL[Google Calendar Exporter]
    
    %% Enrichers Subcomponents
    EN --> EN_GMAIL[Gmail Enricher]
    
    %% Stores Subcomponents
    ST --> ST_ES[Elasticsearch]
    ST --> ST_VS[Vector Store]
    ST --> ST_DOC[Document Store]
    ST --> ST_RAG[RAG Manager]
    
    %% Management AI Subcomponents
    MA --> MA_REP[Reporting]
    MA --> MA_AGENT[Agent Supervisor]
    MA --> MA_AUTOGEN[Autogen Agents]
    MA --> MA_LANGGRAPH[LangGraph Agents]
```

## Detailed Data Flow

### 1. Data Collection Flow

```mermaid
flowchart TD
    %% Slack Data Flow
    SLACK_START[Start Slack Backup Flow] --> SLACK_TOKEN[Get Slack Token & Cookie]
    SLACK_TOKEN --> SLACK_TIMESTAMP[Get Last Successful Timestamp]
    SLACK_TIMESTAMP --> SLACK_BACKUP[Perform Backup]
    SLACK_BACKUP --> SLACK_POSTPROCESS[Postprocess JSON Files]
    SLACK_POSTPROCESS --> SLACK_STORE[Store in Vector DB]
    
    %% Gmail Data Flow
    GMAIL_START[Start Gmail Backup Flow] --> GMAIL_RETRIEVE[Retrieve Messages]
    GMAIL_RETRIEVE --> GMAIL_PROCESS[Process Messages]
    GMAIL_PROCESS --> GMAIL_STORE_RAW[Store Raw in Elasticsearch]
    GMAIL_STORE_RAW --> GMAIL_ENRICH[Process Emails by Google IDs]
    GMAIL_ENRICH --> GMAIL_ANALYZE[Utilize Analysis]
    GMAIL_ANALYZE --> GMAIL_STORE_VS[Store in Vector Store]
    
    %% Jira Data Flow
    JIRA_START[Start Jira Backup] --> JIRA_FETCH[Fetch Issues]
    JIRA_FETCH --> JIRA_PROCESS[Process Issues]
    JIRA_PROCESS --> JIRA_STORE[Store in Elasticsearch]
    
    %% Bitbucket Data Flow
    BB_START[Start Bitbucket Backup] --> BB_FETCH[Fetch PRs]
    BB_FETCH --> BB_PROCESS[Process PRs]
    BB_PROCESS --> BB_STORE[Store in Elasticsearch]
    
    %% Slab Data Flow
    SLAB_START[Start Slab Backup] --> SLAB_FETCH[Fetch Documents]
    SLAB_FETCH --> SLAB_PROCESS[Process Documents]
    SLAB_PROCESS --> SLAB_STORE[Store in Elasticsearch]
```

### 2. Data Processing Flow

```mermaid
flowchart TD
    %% Slack Processing
    SLACK_JSON[Slack JSON Files] --> SLACK_PARSE[Parse Messages]
    SLACK_PARSE --> SLACK_ADD_META[Add Metadata]
    SLACK_ADD_META --> SLACK_FILTER[Filter Complex Metadata]
    SLACK_FILTER --> SLACK_EMBED[Generate Embeddings]
    SLACK_EMBED --> SLACK_STORE_ES[Store in Elasticsearch]
    
    %% Gmail Processing
    GMAIL_RAW[Gmail Raw Messages] --> GMAIL_EXTRACT[Extract Email Body]
    GMAIL_EXTRACT --> GMAIL_PARSE[Parse Date & Labels]
    GMAIL_PARSE --> GMAIL_ANALYZE[LLM Analysis]
    GMAIL_ANALYZE --> GMAIL_CATEGORIZE[Categorize & Label]
    GMAIL_CATEGORIZE --> GMAIL_STORE_ES[Store in Elasticsearch]
    
    %% Document Storage
    DOC_RECEIVE[Receive Documents] --> DOC_DEDUP[Deduplicate]
    DOC_DEDUP --> DOC_BATCH[Batch Process]
    DOC_BATCH --> DOC_EMBED[Generate Embeddings]
    DOC_EMBED --> DOC_STORE_ES[Store in Elasticsearch]
```

### 3. Reporting Flow

```mermaid
flowchart TD
    %% Report Generation
    REP_START[Start Report Generation] --> REP_QUERY[Get Report Query]
    REP_QUERY --> REP_DOCS[Get Documents]
    REP_DOCS --> REP_FORMAT[Document Formatter]
    REP_FORMAT --> REP_SUMMARIZE[Document Summarizer]
    REP_SUMMARIZE --> REP_WRITE[Report Writer]
    REP_WRITE --> REP_REVIEW[Reviewer]
    REP_REVIEW --> REP_DECISION{Is Finished?}
    REP_DECISION -->|Yes| REP_FINALIZE[Finalize Report]
    REP_DECISION -->|No| REP_WRITE
    REP_FINALIZE --> REP_SAVE[Save Report]
    
    %% Secretary Report
    SEC_START[Start Secretary Report] --> SEC_QUERY[Get Report Query]
    SEC_QUERY --> SEC_DOCS[Get Documents]
    SEC_DOCS --> SEC_JIRA[Get Jira Issues]
    SEC_DOCS --> SEC_EMAIL[Get Emails]
    SEC_DOCS --> SEC_SLACK[Get Slack Messages]
    SEC_DOCS --> SEC_BB[Get Bitbucket PRs]
    SEC_JIRA & SEC_EMAIL & SEC_SLACK & SEC_BB --> SEC_COMBINE[Combine Documents]
    SEC_COMBINE --> SEC_REPORT[Run Report]
    SEC_REPORT --> SEC_WRITE[Write Reports]
```

## Component Interactions

### Data Getters to Stores

```mermaid
flowchart TD
    %% Data Flow from Getters to Stores
    DG_SLACK[Slack Backup] --> EX_SLACK[Slack Exporter]
    EX_SLACK --> ST_ES[Elasticsearch]
    EX_SLACK --> ST_VS[Vector Store]
    
    DG_GMAIL[Gmail Backup] --> EX_GMAIL[Gmail Exporter]
    EX_GMAIL --> EN_GMAIL[Gmail Enricher]
    EN_GMAIL --> ST_ES
    EN_GMAIL --> ST_VS
    
    DG_JIRA[Jira Backup] --> EX_JIRA[Jira Exporter]
    EX_JIRA --> ST_ES
    
    DG_BITBUCKET[Bitbucket Backup] --> EX_BB[Bitbucket Exporter]
    EX_BB --> ST_ES
    
    DG_SLAB[Slab Backup] --> EX_SLAB[Slab Exporter]
    EX_SLAB --> ST_ES
    EX_SLAB --> ST_VS
```

### Stores to Management AI

```mermaid
flowchart TD
    %% Data Flow from Stores to Management AI
    ST_ES[Elasticsearch] --> ST_RAG[RAG Manager]
    ST_VS[Vector Store] --> ST_RAG
    
    ST_RAG --> MA_REP[Reporting]
    ST_RAG --> MA_AGENT[Agent Supervisor]
    
    MA_REP --> REP_SEC[Secretary Reports]
    MA_REP --> REP_OKR[OKR Reports]
    MA_REP --> REP_PEOPLE[People Reports]
    
    MA_AGENT --> AGENT_AUTO[Autogen Agents]
    MA_AGENT --> AGENT_LANG[LangGraph Agents]
```

## Key Processes

1. **Data Collection**: The system collects data from various sources (Slack, Gmail, Jira, Bitbucket, Slab, Google Calendar)
2. **Data Processing**: The collected data is processed and formatted
3. **Data Enrichment**: The processed data is enriched with additional information (especially for Gmail)
4. **Data Storage**: The enriched data is stored in Elasticsearch and Vector Stores
5. **Report Generation**: Reports are generated from the stored data using LLMs and agent frameworks
6. **Agent Interaction**: Various agent frameworks (Autogen, LangGraph) are used to interact with the data

This flow diagram provides a comprehensive overview of all the actions taken in the src directory, showing how data flows through the system from collection to reporting.