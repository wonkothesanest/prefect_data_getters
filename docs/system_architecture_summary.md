# System Architecture and Data Flow Summary

## Overview

The system is designed to collect, process, store, and analyze data from various sources to generate insightful reports. It follows a modular architecture with clear separation of concerns between data collection, processing, storage, and reporting components.

## Key Components

### 1. Data Getters

The Data Getters module is responsible for collecting data from various external sources. Each source has a dedicated flow implemented as a Prefect flow:

- **Slack Backup Flow**: Collects messages from Slack channels, groups, and direct messages
- **Gmail Backup Flow**: Retrieves emails from Gmail
- **Jira Backup Flow**: Fetches issues from Jira
- **Bitbucket Backup Flow**: Collects pull requests from Bitbucket
- **Slab Backup Flow**: Retrieves documents from Slab
- **Google Calendar Backup Flow**: Collects calendar events from Google Calendar

These flows are designed to be run periodically to keep the data up-to-date. They handle authentication, pagination, rate limiting, and error handling for each data source.

### 2. Exporters

The Exporters module processes the raw data collected by the Data Getters and transforms it into a standardized format. Each data source has a dedicated exporter:

- **Slack Exporter**: Processes Slack messages, adding metadata like usernames and channel names
- **Gmail Exporter**: Extracts email bodies, parses dates, and formats email metadata
- **Jira Exporter**: Processes Jira issues, extracting relevant fields
- **Bitbucket Exporter**: Processes pull requests, extracting relevant information
- **Slab Exporter**: Processes Slab documents, extracting content and metadata

The exporters ensure that data from different sources is formatted consistently for storage and analysis.

### 3. Enrichers

The Enrichers module enhances the processed data with additional information, often using AI techniques:

- **Gmail Enricher**: Analyzes emails using LLMs to extract key information, categorize emails, and suggest labels

This module is particularly important for unstructured data like emails, where AI can extract valuable insights that would be difficult to obtain through rule-based processing.

### 4. Stores

The Stores module is responsible for storing the processed and enriched data:

- **Elasticsearch Store**: Stores raw and processed data in Elasticsearch indices
- **Vector Store**: Stores vector embeddings of documents for similarity search
- **Document Store**: Manages document storage and retrieval
- **RAG Manager**: Provides a unified interface for retrieval-augmented generation across multiple data sources

The storage layer is designed to support efficient retrieval of data for reporting and analysis.

### 5. Management AI

The Management AI module generates reports and insights from the stored data:

- **Reporting**: Generates various types of reports (Secretary, OKR, People)
- **Agent Supervisor**: Coordinates agent activities
- **Autogen Agents**: Implements multi-agent conversations
- **LangGraph Agents**: Implements graph-based agent workflows

This module leverages AI techniques to analyze the data and generate actionable insights.

## Data Flow

### 1. Collection Phase

The data flow begins with the collection of data from various sources:

1. **Authentication**: Each data getter authenticates with its respective API
2. **Timestamp Management**: The system tracks the last successful run to avoid duplicate data collection
3. **Pagination**: For large datasets, the system handles pagination to retrieve all data
4. **Rate Limiting**: The system respects API rate limits to avoid being throttled
5. **Error Handling**: Errors during data collection are logged and handled appropriately

### 2. Processing Phase

Once data is collected, it goes through a processing phase:

1. **Parsing**: Raw data is parsed into a structured format
2. **Metadata Extraction**: Relevant metadata is extracted from the raw data
3. **Content Extraction**: The main content is extracted from the raw data
4. **Formatting**: The data is formatted consistently across different sources
5. **Deduplication**: Duplicate data is identified and removed

### 3. Enrichment Phase

For some data sources, particularly emails, the data goes through an enrichment phase:

1. **AI Analysis**: LLMs analyze the content to extract key information
2. **Categorization**: The data is categorized based on its content
3. **Labeling**: Labels are applied to the data for better organization
4. **Summarization**: Long content is summarized for easier consumption
5. **Entity Extraction**: Entities like people, projects, and teams are extracted

### 4. Storage Phase

The processed and enriched data is then stored:

1. **Raw Storage**: Raw data is stored in Elasticsearch for reference
2. **Processed Storage**: Processed data is stored in Elasticsearch for querying
3. **Vector Storage**: Vector embeddings are stored for similarity search
4. **Metadata Indexing**: Metadata is indexed for efficient filtering
5. **Document Management**: Documents are managed for retrieval

### 5. Reporting Phase

Finally, the stored data is used to generate reports:

1. **Query Formulation**: A query is formulated based on the report requirements
2. **Document Retrieval**: Relevant documents are retrieved from the storage layer
3. **Document Formatting**: Retrieved documents are formatted for processing
4. **Summarization**: Documents are summarized to extract key information
5. **Report Writing**: A report is generated based on the summarized documents
6. **Review**: The report is reviewed for quality
7. **Finalization**: If the report passes review, it is finalized and saved

## Key Workflows

### 1. Slack Backup Workflow

1. The system authenticates with Slack using a token and cookie
2. It retrieves the last successful run timestamp to avoid duplicate data collection
3. It collects messages from public channels, private groups, and direct messages
4. For each channel/group/DM, it retrieves the message history and thread replies
5. Messages are parsed and written to JSON files organized by date
6. JSON files are post-processed to add metadata like usernames and channel names
7. Processed messages are stored in Elasticsearch with vector embeddings

### 2. Gmail Backup Workflow

1. The system retrieves Gmail messages from a specified time period
2. Raw messages are stored in Elasticsearch with minimal processing
3. Messages are processed to extract bodies, parse dates, and add metadata
4. Emails are analyzed using LLMs to extract key information
5. Based on the analysis, emails are labeled for better organization
6. Processed emails are stored with vector embeddings for retrieval

### 3. Reporting Workflow

1. The system retrieves relevant documents from various sources based on a time range
2. Documents are formatted for processing
3. Documents are summarized to extract key information
4. A report is generated based on the summarized documents
5. The report is reviewed for quality
6. If the report passes review, it is finalized and saved

## Technical Implementation

The system is implemented using Python with the following key libraries and frameworks:

- **Prefect**: For workflow orchestration
- **Elasticsearch**: For data storage and retrieval
- **LangChain**: For AI components and RAG
- **HuggingFace**: For embeddings generation
- **LangGraph**: For agent workflows
- **Autogen**: For multi-agent conversations
- **OpenAI**: For LLM capabilities

The code is organized into modules that correspond to the key components described above, with clear separation of concerns and well-defined interfaces between components.

## Conclusion

The system represents a comprehensive solution for collecting, processing, storing, and analyzing data from various sources. Its modular architecture allows for easy extension to new data sources and use cases, while its AI capabilities enable the extraction of valuable insights from unstructured data.