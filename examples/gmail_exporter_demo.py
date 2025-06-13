#!/usr/bin/env python3
"""
Gmail Exporter Demo

This script demonstrates how to use the new GmailExporter class
that inherits from BaseExporter.
"""

import sys
import os

# Add src to path for demo purposes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from prefect_data_getters.exporters.gmail_exporter import GmailExporter
from prefect_data_getters.exporters.gmail import get_labels  # Backward compatibility


def demo_new_gmail_exporter():
    """Demonstrate the new GmailExporter class."""
    print("=== New GmailExporter Demo ===")
    
    # Create exporter with custom configuration
    config = {
        "token_path": "secrets/gmail_token.pickle",
        "credentials_path": "secrets/google_app_creds.json",
        "oauth_port": 8080
    }
    
    exporter = GmailExporter(config)
    
    print(f"Exporter created: {exporter}")
    print(f"Config: {exporter.config}")
    
    # Show the export method signature
    import inspect
    sig = inspect.signature(exporter.export)
    print(f"Export method signature: {sig}")
    
    # Note: We can't actually run export without authentication
    print("To use the exporter:")
    print("1. documents = exporter.export(days_ago=7)")
    print("2. documents = exporter.export(query='from:example@gmail.com')")
    print("3. documents = exporter.export(days_ago=30, max_results=100)")
    
    print("\nThe export method returns an Iterator[Document] for memory efficiency.")


def demo_backward_compatibility():
    """Demonstrate backward compatibility."""
    print("\n=== Backward Compatibility Demo ===")
    
    # Import old functions - these will show deprecation warnings
    from prefect_data_getters.exporters.gmail import (
        authenticate_gmail,
        get_messages,
        get_labels,
        GmailExporter as BackwardCompatGmailExporter
    )
    
    print("Backward compatibility functions imported successfully:")
    print(f"- authenticate_gmail: {authenticate_gmail}")
    print(f"- get_messages: {get_messages}")
    print(f"- get_labels: {get_labels}")
    print(f"- GmailExporter: {BackwardCompatGmailExporter}")
    
    print("\nNote: These functions will show deprecation warnings when used.")


def demo_inheritance():
    """Demonstrate inheritance from BaseExporter."""
    print("\n=== Inheritance Demo ===")
    
    from prefect_data_getters.exporters.base import BaseExporter
    
    exporter = GmailExporter()
    
    print(f"Is instance of BaseExporter: {isinstance(exporter, BaseExporter)}")
    print(f"Has export method: {hasattr(exporter, 'export')}")
    print(f"Has error handling methods: {hasattr(exporter, '_handle_api_error')}")
    print(f"Has logging methods: {hasattr(exporter, '_log_export_start')}")
    
    # Show method resolution order
    print(f"Method Resolution Order: {[cls.__name__ for cls in GmailExporter.__mro__]}")


def demo_processing_pipeline():
    """Demonstrate how to use with processing functions."""
    print("\n=== Processing Pipeline Demo ===")
    
    from prefect_data_getters.exporters import (
        add_ingestion_timestamp,
        add_source_metadata,
        convert_to_ai_documents
    )
    
    print("Example processing pipeline:")
    print("""
    # Create exporter
    exporter = GmailExporter()
    
    # Export documents
    documents = exporter.export(days_ago=7)
    
    # Process documents through pipeline
    processed_docs = add_ingestion_timestamp(documents)
    processed_docs = add_source_metadata(processed_docs, "gmail", "email")
    ai_documents = convert_to_ai_documents(processed_docs, "email_messages")
    
    # Convert to list for storage
    final_docs = list(ai_documents)
    """)


if __name__ == "__main__":
    demo_new_gmail_exporter()
    demo_backward_compatibility()
    demo_inheritance()
    demo_processing_pipeline()
    
    print("\n=== Demo Complete ===")
    print("The Gmail exporter has been successfully refactored to use the BaseExporter architecture!")