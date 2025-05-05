# Google Drive MCP Server Integration

This project demonstrates how to use the Google Drive MCP (Model Context Protocol) server to query Google Drive files with a language model.

## Overview

The Google Drive MCP server provides integration with Google Drive, allowing you to:
- List and search files in your Google Drive
- Read file contents across various document formats
- Query file contents using language models

The server handles file type conversions automatically:
- Google Docs → Markdown
- Google Sheets → CSV
- Google Presentations → Plain text
- Google Drawings → PNG
- Other files → Native format

## Prerequisites

Before using the Google Drive MCP server, you need to set up authentication with Google Cloud:

1. Create a new Google Cloud project
2. Enable the Google Drive API
3. Configure an OAuth consent screen ("internal" is fine for testing)
4. Add OAuth scope `https://www.googleapis.com/auth/drive.readonly`
5. Create an OAuth Client ID (you can use either option):
   - **Option A: Desktop Application** (simpler for local testing)
     - Create an OAuth Client ID for application type "Desktop App"
   - **Option B: Web Application** (better for production use)
     - Create an OAuth Client ID for application type "Web Application"
     - Add `http://localhost:3000/oauth2callback` as an authorized redirect URI
     - Add `http://localhost:3000` as an authorized JavaScript origin
6. Download the JSON file of your client's OAuth keys
7. Rename the key file to `gcp-oauth.keys.json` and place it in the `credentials` directory

## Installation

The Google Drive MCP server has been configured in the MCP settings file. It uses NPX to run the server:

```json
{
  "mcpServers": {
    "gdrive": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-gdrive"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

## Authentication Setup

### Setting Up Your OAuth Credentials

1. Copy your downloaded OAuth credentials file to the credentials directory:
   ```bash
   cp /path/to/downloaded/client_secret_*.json ./credentials/gcp-oauth.keys.json
   ```

2. Make sure your OAuth credentials file contains either:
   - The `"installed"` key for Desktop Application OAuth
   - The `"web"` key for Web Application OAuth

### Authentication Process

When you first use the MCP server, you'll need to authenticate with Google:

1. Start the server using one of the methods below
2. The server will prompt you to open a URL in your browser
3. Complete the Google authentication process
4. For Web Application OAuth:
   - You'll be redirected to `http://localhost:3000/oauth2callback`
   - The server will automatically capture the authorization code
5. For Desktop Application OAuth:
   - You'll be given a code to copy and paste back to the terminal
6. Credentials will be saved for future use as `.gdrive-server-credentials.json`

### Starting the Server

#### Option 1: Using NPX (Recommended for development)

```bash
npx -y @modelcontextprotocol/server-gdrive
```

#### Option 2: Using Docker

```bash
docker-compose up gdrive-mcp
```

## Usage

### Using the Test Scripts

#### Command-line Interface

The `gdrive_query.py` script provides a command-line interface for interacting with the Google Drive MCP server:

Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your_api_key
```

Run a test query:
```bash
python gdrive_query.py test
```

Search for files:
```bash
python gdrive_query.py search "project proposal"
```

Query a file:
```bash
python gdrive_query.py query "file_id" "What is the budget for this project?"
```

#### Direct MCP Tool Usage

The `mcp_direct_test.py` script demonstrates how to use the MCP tools directly in your code:

```bash
python mcp_direct_test.py
```

This script shows how to:
1. Search for files using the `search_files` MCP tool
2. Query file content using the `query_file_content` MCP tool
3. Process the results with a language model

#### Docker Compose

You can also run everything using Docker Compose:

```bash
docker-compose up
```

This will start both the Google Drive MCP server and the Python client.

### Using MCP Tools Directly

Once the MCP server is connected, you can use the following tools:

1. `search_files` - Search for files in Google Drive
   - Input: A search query string and optional maximum results
   - Returns: File names and metadata of matching files

2. `query_file_content` - Query the content of a file using a language model
   - Input: A file ID and a question
   - Returns: Answer from the language model about the file content

## Notes

- The current implementation in `gdrive_query.py` simulates the MCP server responses for demonstration purposes.
- When the MCP server is properly connected, you would use the actual MCP tools instead of the simulated responses.
- The script uses OpenAI's GPT-4o model by default, but you can change it to any model you prefer.