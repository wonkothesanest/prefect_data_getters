"""
Base exporter abstract class for all data exporters.

This module provides the abstract base class that all data exporters must inherit from,
ensuring a consistent interface and common functionality across all exporters.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Any
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """
    Abstract base class for all data exporters.
    
    This class defines the common interface that all exporters must implement,
    providing a consistent way to export documents from various data sources.
    All concrete exporters must inherit from this class and implement the
    abstract export method.
    
    Attributes:
        config: Optional configuration dictionary for the exporter
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base exporter.
        
        Args:
            config: Optional configuration dictionary containing exporter-specific
                   settings such as authentication credentials, API endpoints, etc.
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def export(self, **kwargs) -> Iterator[Any]:
        """
        Export raw data from the data source.
        
        This method must be implemented by all concrete exporter classes.
        It should yield raw data objects (dicts, API responses, etc.) from
        the specific data source without processing them into Documents.
        
        Args:
            **kwargs: Exporter-specific parameters for filtering, pagination,
                     authentication, etc. Each concrete exporter will define
                     its own specific parameter signature.
        
        Returns:
            Iterator[Any]: An iterator yielding raw data objects from
                          the data source (typically dicts or API response objects).
        
        Raises:
            NotImplementedError: If not implemented by concrete class.
        """
        pass
    
    @abstractmethod
    def process(self, raw_data: Iterator[Any]) -> Iterator[Document]:
        """
        Process raw data into Document objects.
        
        This method must be implemented by all concrete exporter classes.
        It should convert raw data objects into langchain Document objects
        with appropriate content and metadata.
        
        Args:
            raw_data: Iterator of raw data objects from export() method
        
        Returns:
            Iterator[Document]: An iterator yielding Document objects
                              processed from the raw data.
        
        Raises:
            NotImplementedError: If not implemented by concrete class.
        """
        pass
    
    def export_documents(self, **kwargs) -> Iterator[Document]:
        """
        Convenience method that combines export and process.
        
        This method calls export() to get raw data, then process() to convert
        it to Documents. This maintains backward compatibility while allowing
        separate access to raw data and processed documents.
        
        Args:
            **kwargs: Parameters passed to export() method
            
        Returns:
            Iterator[Document]: An iterator yielding processed Document objects
        """
        raw_data = self.export(**kwargs)
        return self.process(raw_data)
    
    def _handle_authentication_error(self, error: Exception) -> None:
        """
        Handle authentication errors in a consistent way.
        
        Args:
            error: The authentication error that occurred
            
        Raises:
            Exception: Re-raises the error after logging
        """
        self.logger.error(f"Authentication error in {self.__class__.__name__}: {error}")
        raise error
    
    def _handle_api_error(self, error: Exception, context: str = "") -> None:
        """
        Handle API errors in a consistent way.
        
        Args:
            error: The API error that occurred
            context: Additional context about when the error occurred
            
        Raises:
            Exception: Re-raises the error after logging
        """
        context_msg = f" during {context}" if context else ""
        self.logger.error(f"API error in {self.__class__.__name__}{context_msg}: {error}")
        raise error
    
    def _log_export_start(self, **kwargs) -> None:
        """
        Log the start of an export operation.
        
        Args:
            **kwargs: Export parameters to include in the log
        """
        params_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(f"Starting export from {self.__class__.__name__} with parameters: {params_str}")
    
    def _log_export_complete(self, document_count: int) -> None:
        """
        Log the completion of an export operation.
        
        Args:
            document_count: Number of documents exported
        """
        self.logger.info(f"Completed export from {self.__class__.__name__}: {document_count} documents")
    
    def _validate_config(self, required_keys: list[str]) -> None:
        """
        Validate that required configuration keys are present.
        
        Args:
            required_keys: List of configuration keys that must be present
            
        Raises:
            ValueError: If any required keys are missing
        """
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            raise ValueError(
                f"{self.__class__.__name__} missing required configuration keys: {missing_keys}"
            )