# Detailed Data Flow Analysis

This document provides a more detailed analysis of how data flows through the system, focusing on the specific transformations and processing steps for each data source.

## 1. Slack Data Flow

```mermaid
flowchart TD
    %% Slack Data Collection and Processing
    S1[slack_backup_flow] --> S2[perform_backup]
    S2 --> S3[do_backup]
    S3 --> S4[bootstrapKeyValues]
    S4 --> S5[fetchPublicChannels]
    S4 --> S6[fetchGroups]
    S4 --> S7[fetchDirectMessages]
    S5 & S6 & S7 --> S8[getHistory]
    S8 --> S9[getReplies]
    S8 --> S10[parseMessages]
    S10 --> S11[writeMessageFile]
    S11 --> S12[JSON Files]
    S12 --> S13[postprocess_json_files]
    S13 --> S14[process_slack_messages]
    S14 --> S15[replace_user_mentions]
    S14 --> S16[add_metadata]
    S15 & S16 --> S17[filter_complex_metadata]
    S17 --> S18[store_vector_db]
    S18 --> S19[batch_process_and_store]
    S19 --> S20[ESVectorStore]
    S20 --> S21[Elasticsearch]
```

### Key Slack Processing Steps:
1. **Collection**: The system authenticates with Slack and collects messages from public channels, private groups, and direct messages
2. **History Retrieval**: For each channel/group/DM, it retrieves the message history and thread replies
3. **Message Parsing**: Messages are parsed and written to JSON files organized by date
4. **Post-processing**: JSON files are post-processed to add metadata like usernames and channel names
5. **Storage**: Processed messages are stored in Elasticsearch with vector embeddings

## 2. Gmail Data Flow

```mermaid
flowchart TD
    %% Gmail Data Collection and Processing
    G1[gmail_flow] --> G2[gmail_mbox_backup_flow]
    G2 --> G3[retrieve_messages]
    G3 --> G4[get_messages]
    G4 --> G5[Raw Messages]
    G5 --> G6[get_email_body]
    G5 --> G7[parse_date]
    G6 & G7 --> G8[upsert_documents]
    G8 --> G9[Elasticsearch Raw]
    G5 --> G10[process_messages]
    G10 --> G11[process_message]
    G11 --> G12[store_documents_in_vectorstore]
    G12 --> G13[batch_process_and_store]
    G13 --> G14[ESVectorStore]
    G14 --> G15[Elasticsearch]
    G2 --> G16[process_emails_by_google_ids]
    G16 --> G17[process_email_and_upsert]
    G17 --> G18[EmailExtractor.parse_email]
    G18 --> G19[Elasticsearch Processed]
    G2 --> G20[utilize_analysis_flow]
    G20 --> G21[utilize_analysis]
    G21 --> G22[apply_labels_to_email]
```

### Key Gmail Processing Steps:
1. **Collection**: The system retrieves Gmail messages from a specified time period
2. **Raw Storage**: Raw messages are stored in Elasticsearch with minimal processing
3. **Processing**: Messages are processed to extract bodies, parse dates, and add metadata
4. **LLM Analysis**: Emails are analyzed using LLMs to extract key information
5. **Labeling**: Based on the analysis, emails are labeled for better organization
6. **Vector Storage**: Processed emails are stored with vector embeddings for retrieval

## 3. Jira Data Flow

```mermaid
flowchart TD
    %% Jira Data Collection and Processing
    J1[jira_backup] --> J2[fetch_issues]
    J2 --> J3[process_issues]
    J3 --> J4[add_metadata]
    J4 --> J5[upsert_documents]
    J5 --> J6[Elasticsearch]
```

## 4. Bitbucket Data Flow

```mermaid
flowchart TD
    %% Bitbucket Data Collection and Processing
    B1[bitbucket_backup] --> B2[fetch_pull_requests]
    B2 --> B3[process_pull_requests]
    B3 --> B4[add_metadata]
    B4 --> B5[upsert_documents]
    B5 --> B6[Elasticsearch]
```

## 5. Slab Data Flow

```mermaid
flowchart TD
    %% Slab Data Collection and Processing
    SL1[slab_backup] --> SL2[fetch_documents]
    SL2 --> SL3[process_documents]
    SL3 --> SL4[add_metadata]
    SL4 --> SL5[upsert_documents]
    SL5 --> SL6[Elasticsearch]
    SL4 --> SL7[store_vector_db]
    SL7 --> SL8[ESVectorStore]
    SL8 --> SL9[Elasticsearch Vectors]
```

## 6. Reporting Flow

```mermaid
flowchart TD
    %% Reporting Process
    R1[generate_people_reports] --> R2[_get_documents]
    R2 --> R3[search_boring_search - jira]
    R2 --> R4[search_boring_search - emails]
    R2 --> R5[search_boring_search - slack]
    R2 --> R6[search_boring_search - bitbucket]
    R3 & R4 & R5 & R6 --> R7[all_docs]
    R7 --> R8[run_report]
    R8 --> R9[document_formatter]
    R9 --> R10[document_summarizer]
    R10 --> R11[process_document]
    R11 --> R12[summarization_prompt]
    R12 --> R13[doc_reviewer_llm]
    R13 --> R14[report_writer]
    R14 --> R15[report_prompt]
    R15 --> R16[llm]
    R16 --> R17[reviewer]
    R17 --> R18[review_prompt]
    R18 --> R19[llm]
    R19 --> R20{is_finished?}
    R20 -->|No| R14
    R20 -->|Yes| R21[write_reports]
```

### Key Reporting Steps:
1. **Document Retrieval**: The system retrieves relevant documents from various sources
2. **Document Formatting**: Documents are formatted for processing
3. **Summarization**: Documents are summarized to extract key information
4. **Report Writing**: A report is generated based on the summarized documents
5. **Review**: The report is reviewed for quality
6. **Finalization**: If the report passes review, it is finalized and saved

## 7. Data Store Architecture

```mermaid
flowchart TD
    %% Data Store Architecture
    DS1[Raw Data] --> DS2[Elasticsearch Raw Indices]
    DS2 --> DS3[Processed Data]
    DS3 --> DS4[Elasticsearch Processed Indices]
    DS3 --> DS5[Vector Embeddings]
    DS5 --> DS6[Vector Stores]
    DS6 --> DS7[RAG Manager]
    DS4 --> DS7
    DS7 --> DS8[MultiSourceSearcher]
    DS8 --> DS9[Management AI]
```

### Key Data Store Components:
1. **Raw Indices**: Store raw data from various sources
2. **Processed Indices**: Store processed and enriched data
3. **Vector Stores**: Store vector embeddings for similarity search
4. **RAG Manager**: Manages retrieval-augmented generation across multiple sources
5. **MultiSourceSearcher**: Provides a unified interface for searching across all data sources

## 8. Agent Architecture

```mermaid
flowchart TD
    %% Agent Architecture
    A1[Agent Supervisor] --> A2[Autogen Agents]
    A1 --> A3[LangGraph Agents]
    A2 --> A4[Multi-Agent Chat]
    A3 --> A5[StateGraph]
    A5 --> A6[DocumentFormatter]
    A6 --> A7[Summarizer]
    A7 --> A8[ReportWriter]
    A8 --> A9[Reviewer]
```

### Key Agent Components:
1. **Agent Supervisor**: Coordinates agent activities
2. **Autogen Agents**: Implements multi-agent conversations
3. **LangGraph Agents**: Implements graph-based agent workflows
4. **StateGraph**: Manages state transitions in agent workflows
5. **Specialized Nodes**: Handle specific tasks in the workflow (formatting, summarizing, writing, reviewing)

## 9. End-to-End Data Flow

```mermaid
flowchart TD
    %% End-to-End Data Flow
    E1[Data Sources] --> E2[Data Getters]
    E2 --> E3[Exporters]
    E3 --> E4[Enrichers]
    E4 --> E5[Stores]
    E5 --> E6[RAG Manager]
    E6 --> E7[Management AI]
    E7 --> E8[Reports]
    
    %% Data Sources
    E1 --> E1_1[Slack]
    E1 --> E1_2[Gmail]
    E1 --> E1_3[Jira]
    E1 --> E1_4[Bitbucket]
    E1 --> E1_5[Slab]
    
    %% Reports
    E8 --> E8_1[Secretary Reports]
    E8 --> E8_2[OKR Reports]
    E8 --> E8_3[People Reports]
```

This detailed data flow analysis provides a comprehensive view of how data moves through the system, from collection to reporting, highlighting the specific transformations and processing steps for each data source.