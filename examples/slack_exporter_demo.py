"""
Slack Exporter Demo

This script demonstrates how to use the SlackExporter to export Slack messages
from various channels and process them into documents.
"""

import os
import sys
from datetime import datetime
from typing import List

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from prefect_data_getters.exporters.slack_exporter import SlackExporter
from prefect_data_getters.exporters import add_ingestion_timestamp, convert_to_ai_documents
from prefect_data_getters.stores.document_types.slack_document import SlackMessageDocument


def demo_basic_export():
    """Demonstrate basic Slack message export."""
    print("=== Basic Slack Export Demo ===")
    
    # Configuration for Slack API
    config = {
        'token': os.getenv('SLACK_TOKEN', 'xoxb-your-slack-token-here'),
        'page_size': 100,  # Smaller page size for demo
        'rate_limit_delay': 1.0  # Be respectful to Slack API
    }
    
    # Create exporter
    exporter = SlackExporter(config)
    
    try:
        # Export messages from the last 3 days
        print("Exporting Slack messages from the last 3 days...")
        documents = list(exporter.export(days_ago=3, limit=10))  # Limit for demo
        
        print(f"Exported {len(documents)} messages")
        
        # Display first few messages
        for i, doc in enumerate(documents[:3]):
            print(f"\n--- Message {i+1} ---")
            print(f"Channel: {doc.metadata.get('channel', 'Unknown')}")
            print(f"User: {doc.metadata.get('user', 'Unknown')}")
            print(f"Timestamp: {doc.metadata.get('ts_datetime', 'Unknown')}")
            print(f"Content: {doc.page_content[:100]}...")
            if doc.metadata.get('thread_ts'):
                print("(This is a thread reply)")
            
    except Exception as e:
        print(f"Error during export: {e}")
        print("Make sure you have set the SLACK_TOKEN environment variable")


def demo_channel_specific_export():
    """Demonstrate exporting from specific channels."""
    print("\n=== Channel-Specific Export Demo ===")
    
    config = {
        'token': os.getenv('SLACK_TOKEN', 'xoxb-your-slack-token-here'),
        'page_size': 50
    }
    
    exporter = SlackExporter(config)
    
    try:
        # First, let's see what channels are available
        print("Available channels:")
        channels = exporter.get_channels()
        for channel_id, channel_name in list(channels.items())[:10]:  # Show first 10
            print(f"  {channel_name} ({channel_id})")
        
        # Export from specific channels
        target_channels = ['general', 'random']  # Common channel names
        print(f"\nExporting from channels: {target_channels}")
        
        documents = list(exporter.export(
            channels=target_channels,
            days_ago=1,
            limit=5  # Small limit for demo
        ))
        
        print(f"Exported {len(documents)} messages from specified channels")
        
        # Group by channel
        by_channel = {}
        for doc in documents:
            channel = doc.metadata.get('channel', 'Unknown')
            if channel not in by_channel:
                by_channel[channel] = []
            by_channel[channel].append(doc)
        
        for channel, docs in by_channel.items():
            print(f"\n{channel}: {len(docs)} messages")
            
    except Exception as e:
        print(f"Error during channel-specific export: {e}")


def demo_processing_pipeline():
    """Demonstrate document processing pipeline."""
    print("\n=== Document Processing Pipeline Demo ===")
    
    config = {
        'token': os.getenv('SLACK_TOKEN', 'xoxb-your-slack-token-here'),
        'page_size': 20
    }
    
    exporter = SlackExporter(config)
    
    try:
        # Export documents
        print("Exporting messages...")
        raw_documents = exporter.export(days_ago=1, limit=5)
        
        # Apply processing pipeline
        print("Applying processing pipeline...")
        
        # Add ingestion timestamp
        timestamped_docs = add_ingestion_timestamp(raw_documents)
        
        # Convert to AI documents (Slack-specific document type)
        ai_documents = convert_to_ai_documents(timestamped_docs, "slack_messages")
        
        # Process the documents
        processed_docs = list(ai_documents)
        
        print(f"Processed {len(processed_docs)} documents")
        
        # Display processed documents
        for i, doc in enumerate(processed_docs):
            print(f"\n--- Processed Document {i+1} ---")
            print(f"Type: {type(doc).__name__}")
            print(f"Display ID: {doc.get_display_id()}")
            print(f"User: {doc.user}")
            print(f"Channel: {doc.channel}")
            print(f"Formatted Timestamp: {doc.formatted_timestamp}")
            print(f"Is Thread Reply: {doc.is_thread_reply}")
            print(f"Ingestion Time: {doc.metadata.get('ingestion_timestamp', 'N/A')}")
            print(f"Content: {doc.page_content[:100]}...")
            
    except Exception as e:
        print(f"Error during processing pipeline: {e}")


def demo_user_and_channel_info():
    """Demonstrate getting user and channel information."""
    print("\n=== User and Channel Information Demo ===")
    
    config = {
        'token': os.getenv('SLACK_TOKEN', 'xoxb-your-slack-token-here')
    }
    
    exporter = SlackExporter(config)
    
    try:
        # Get user information
        print("Fetching user information...")
        users = exporter.get_users()
        print(f"Found {len(users)} users")
        
        # Display first few users
        user_items = list(users.items())[:5]
        for user_id, user_name in user_items:
            print(f"  {user_name} ({user_id})")
        
        # Get channel information
        print("\nFetching channel information...")
        channels = exporter.get_channels()
        print(f"Found {len(channels)} channels")
        
        # Display first few channels
        channel_items = list(channels.items())[:5]
        for channel_id, channel_name in channel_items:
            print(f"  #{channel_name} ({channel_id})")
            
    except Exception as e:
        print(f"Error fetching user/channel info: {e}")


def demo_error_handling():
    """Demonstrate error handling and recovery."""
    print("\n=== Error Handling Demo ===")
    
    # Test with invalid token
    config = {
        'token': 'invalid-token',
        'page_size': 10
    }
    
    exporter = SlackExporter(config)
    
    try:
        print("Testing with invalid token...")
        documents = list(exporter.export(limit=1))
        print("Unexpected success!")
        
    except Exception as e:
        print(f"Expected error caught: {e}")
        print("This demonstrates proper error handling for authentication failures")
    
    # Test with missing token
    try:
        print("\nTesting with missing token...")
        bad_exporter = SlackExporter({})
        
    except ValueError as e:
        print(f"Expected configuration error caught: {e}")
        print("This demonstrates proper validation of required configuration")


def main():
    """Run all demo functions."""
    print("Slack Exporter Demo")
    print("==================")
    print()
    print("This demo shows how to use the SlackExporter to extract messages from Slack.")
    print("Make sure to set the SLACK_TOKEN environment variable with your Slack bot token.")
    print()
    
    # Check if token is available
    if not os.getenv('SLACK_TOKEN'):
        print("⚠️  SLACK_TOKEN environment variable not set!")
        print("   Set it with: export SLACK_TOKEN='xoxb-your-slack-token-here'")
        print("   Some demos will fail without a valid token.")
        print()
    
    # Run demos
    demo_basic_export()
    demo_channel_specific_export()
    demo_processing_pipeline()
    demo_user_and_channel_info()
    demo_error_handling()
    
    print("\n=== Demo Complete ===")
    print("Check the SlackExporter documentation for more advanced usage patterns.")


if __name__ == "__main__":
    main()