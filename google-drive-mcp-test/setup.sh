#!/bin/bash

# Google Drive MCP Server Setup Script

echo "Google Drive MCP Server Setup"
echo "============================"
echo

# Check if OAuth credentials exist
if [ ! -f "./credentials/gcp-oauth.keys.json" ]; then
    echo "OAuth credentials not found!"
    echo "Please follow these steps:"
    echo "1. Create a new Google Cloud project"
    echo "2. Enable the Google Drive API"
    echo "3. Configure an OAuth consent screen"
    echo "4. Create an OAuth Client ID (either Desktop or Web Application)"
    echo "   - For Desktop App: Create an OAuth Client ID for application type 'Desktop App'"
    echo "   - For Web App: Create an OAuth Client ID for application type 'Web Application'"
    echo "     and add 'http://localhost:3000/oauth2callback' as an authorized redirect URI"
    echo "5. Download the JSON file of your client's OAuth keys"
    echo "6. Copy it to ./credentials/gcp-oauth.keys.json"
    echo
    echo "A template file is available at ./credentials/gcp-oauth.keys.json.template"
    echo
    exit 1
fi

# Check if the OAuth credentials are in the correct format
if grep -q "\"web\"" "./credentials/gcp-oauth.keys.json"; then
    echo "Web Application OAuth credentials detected."
    echo "Using Web Application OAuth flow."
    OAUTH_TYPE="web"
elif grep -q "\"installed\"" "./credentials/gcp-oauth.keys.json"; then
    echo "Desktop Application OAuth credentials detected."
    echo "Using Desktop Application OAuth flow."
    OAUTH_TYPE="desktop"
else
    echo "Error: Invalid OAuth credentials format."
    echo "The credentials file should contain either 'web' or 'installed' key."
    echo "Please check the template file for examples."
    exit 1
fi

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "OPENAI_API_KEY environment variable is not set!"
    echo "Please set it with: export OPENAI_API_KEY=your_api_key"
    echo
    exit 1
fi

echo "Setting up the Google Drive MCP server..."

# Set environment variables
export GDRIVE_CREDENTIALS_PATH="./credentials/gcp-oauth.keys.json"
export GDRIVE_OAUTH_PORT=3000

echo "OAuth type detected: $OAUTH_TYPE"
echo

# Option 1: Run with NPX
echo "Option 1: Run with NPX"
if [ "$OAUTH_TYPE" = "web" ]; then
    echo "npx -y @modelcontextprotocol/server-gdrive"
    echo "This will start a web server on port 3000 for OAuth authentication."
else
    echo "npx -y @modelcontextprotocol/server-gdrive auth"
fi
echo

# Option 2: Run with Docker
echo "Option 2: Run with Docker"
echo "docker-compose up gdrive-mcp"
echo

echo "After authentication, you can run the test script:"
echo "python gdrive_query.py test"
echo

echo "For direct MCP tool usage example:"
echo "python mcp_direct_test.py"
echo

echo "Setup complete!"