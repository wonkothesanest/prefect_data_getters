"""
Demonstration of the new exporter pattern with separate export() and process() methods.

This example shows how to use the refactored exporters that separate raw data export
from document processing, providing better flexibility and separation of concerns.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from prefect_data_getters.exporters.gmail_exporter import GmailExporter
from prefect_data_getters.exporters.slack_exporter import SlackExporter
from prefect_data_getters.exporters import add_ingestion_timestamp, add_source_metadata


def demo_gmail_pattern():
    """Demonstrate the new Gmail exporter pattern."""
    print("=== Gmail Exporter Pattern Demo ===")
    
    # Configure Gmail exporter
    gmail_config = {
        'credentials_path': 'secrets/google_app_creds.json',
        'token_path': 'secrets/gmail_token.pickle'
    }
    
    exporter = GmailExporter(config=gmail_config)
    
    # Method 1: Export raw data, then process separately
    print("\n1. Separate export and process:")
    try:
        # Export raw Gmail messages
        raw_messages = exporter.export(days_ago=1, max_results=2)
        print("Raw messages exported (first 2):")
        
        raw_list = list(raw_messages)
        for i, msg in enumerate(raw_list[:2]):
            print(f"  Message {i+1}: ID={msg.get('id', 'unknown')[:10]}...")
        
        # Process raw messages into documents
        documents = exporter.process(iter(raw_list))
        processed_docs = list(documents)
        print(f"Processed {len(processed_docs)} documents")
        
        if processed_docs:
            print(f"  First doc preview: {processed_docs[0].page_content[:100]}...")
            
    except Exception as e:
        print(f"  Note: Would work with real credentials. Error: {e}")
    
    # Method 2: Use convenience method (backward compatibility)
    print("\n2. Convenience method (combines export + process):")
    try:
        documents = exporter.export_documents(days_ago=1, max_results=2)
        processed_docs = list(documents)
        print(f"Processed {len(processed_docs)} documents using convenience method")
        
    except Exception as e:
        print(f"  Note: Would work with real credentials. Error: {e}")


def demo_slack_pattern():
    """Demonstrate the new Slack exporter pattern."""
    print("\n=== Slack Exporter Pattern Demo ===")
    
    # Configure Slack exporter
    slack_config = {
        'token': 'xoxb-your-slack-token-here'
    }
    
    exporter = SlackExporter(config=slack_config)
    
    # Method 1: Export raw data, then process separately
    print("\n1. Separate export and process:")
    try:
        # Export raw Slack messages
        raw_messages = exporter.export(channels=['general'], days_ago=1, limit=2)
        print("Raw messages exported:")
        
        raw_list = list(raw_messages)
        for i, msg in enumerate(raw_list[:2]):
            print(f"  Message {i+1}: Channel={msg.get('_channel_name', 'unknown')}")
        
        # Process raw messages into documents
        documents = exporter.process(iter(raw_list))
        processed_docs = list(documents)
        print(f"Processed {len(processed_docs)} documents")
        
    except Exception as e:
        print(f"  Note: Would work with real Slack token. Error: {e}")


def demo_processing_pipeline():
    """Demonstrate processing pipeline with the new pattern."""
    print("\n=== Processing Pipeline Demo ===")
    
    # Simulate raw data
    raw_gmail_data = [
        {
            'id': 'msg_001',
            'threadId': 'thread_001',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Email'},
                    {'name': 'From', 'value': 'test@example.com'},
                    {'name': 'Date', 'value': '2025-06-13T09:00:00Z'}
                ],
                'body': {'data': 'VGVzdCBlbWFpbCBjb250ZW50'}  # base64 encoded "Test email content"
            },
            'snippet': 'Test email content...',
            'labelIds': ['INBOX']
        }
    ]
    
    # Create exporter and process data
    gmail_config = {'credentials_path': 'fake', 'token_path': 'fake'}
    exporter = GmailExporter(config=gmail_config)
    
    try:
        # Process raw data into documents
        documents = exporter.process(iter(raw_gmail_data))
        
        # Apply processing functions
        timestamped = add_ingestion_timestamp(documents)
        with_source = add_source_metadata(timestamped, "gmail", "email")
        
        # Collect results
        final_docs = list(with_source)
        
        print("Processing pipeline results:")
        for doc in final_docs:
            print(f"  Subject: {doc.metadata.get('subject', 'N/A')}")
            print(f"  Source: {doc.metadata.get('source_name', 'N/A')}")
            print(f"  Timestamp: {doc.metadata.get('ingestion_timestamp', 'N/A')}")
            print(f"  Content preview: {doc.page_content[:50]}...")
            
    except Exception as e:
        print(f"Processing pipeline error: {e}")


def demo_flexibility():
    """Demonstrate the flexibility of the new pattern."""
    print("\n=== Flexibility Demo ===")
    
    print("Benefits of the new pattern:")
    print("1. Raw data export: Access to original API responses")
    print("2. Separate processing: Custom document transformation")
    print("3. Caching: Can cache raw data and reprocess differently")
    print("4. Testing: Easy to mock raw data for testing")
    print("5. Debugging: Inspect raw data before processing")
    print("6. Backward compatibility: export_documents() method")


if __name__ == "__main__":
    print("New Exporter Pattern Demonstration")
    print("=" * 50)
    
    demo_gmail_pattern()
    demo_slack_pattern()
    demo_processing_pipeline()
    demo_flexibility()
    
    print("\n" + "=" * 50)
    print("Demo completed!")