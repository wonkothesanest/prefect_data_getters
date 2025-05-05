#!/usr/bin/env python3
"""
MCP Direct Test

This script demonstrates how to use the MCP tools directly when they're available.
"""

import os
import json
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def simulate_mcp_search_files(query):
    """
    Simulate the MCP search_files tool.
    
    In a real implementation with MCP connected, you would use:
    result = use_mcp_tool(
        server_name="gdrive",
        tool_name="search_files",
        arguments={"query": query}
    )
    """
    print(f"[MCP Simulation] Searching for files with query: {query}")
    
    # Simulated response
    return [
        {
            "id": "1abc123def456",
            "name": "Project Proposal.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
        {
            "id": "2ghi789jkl012",
            "name": "Budget Spreadsheet.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
    ]

def simulate_mcp_query_file_content(file_id, question):
    """
    Simulate the MCP query_file_content tool.
    
    In a real implementation with MCP connected, you would use:
    result = use_mcp_tool(
        server_name="gdrive",
        tool_name="query_file_content",
        arguments={"fileId": file_id, "question": question}
    )
    """
    print(f"[MCP Simulation] Querying file {file_id} with question: {question}")
    
    # Simulated file content
    file_content = """
    # Project Proposal
    
    ## Executive Summary
    
    This project aims to implement a new customer relationship management (CRM) system
    to improve customer service and sales tracking. The estimated budget is $150,000
    with a timeline of 6 months for full implementation.
    
    ## Goals
    
    1. Increase customer satisfaction by 25%
    2. Reduce response time by 40%
    3. Improve sales conversion by 15%
    
    ## Timeline
    
    - Month 1-2: Requirements gathering and vendor selection
    - Month 3-4: Implementation and data migration
    - Month 5-6: Testing and training
    """
    
    # Use OpenAI to answer the question
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that answers questions about file content."},
            {"role": "user", "content": f"File content:\n{file_content}\n\nQuestion: {question}"}
        ],
        max_tokens=500
    )
    
    return response.choices[0].message.content

def main():
    """Main function to demonstrate MCP tool usage."""
    print("MCP Direct Test")
    print("==============")
    print()
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it with: export OPENAI_API_KEY=your_api_key")
        return
    
    # Step 1: Search for files
    print("Step 1: Searching for files")
    search_query = "project proposal"
    files = simulate_mcp_search_files(search_query)
    print(f"Found {len(files)} files:")
    print(json.dumps(files, indent=2))
    print()
    
    # Step 2: Query file content
    if files:
        print("Step 2: Querying file content")
        file_id = files[0]["id"]
        question = "What is the budget and timeline for the project?"
        answer = simulate_mcp_query_file_content(file_id, question)
        print("\nAnswer:")
        print(answer)
    
    print("\nTest complete!")
    print("\nNote: This is a simulation. When MCP is properly connected,")
    print("you would use the actual MCP tools instead of these simulated functions.")

if __name__ == "__main__":
    main()