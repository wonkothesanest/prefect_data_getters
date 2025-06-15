"""
Calendar document type implementation.
"""

from prefect_data_getters.stores.documents_new import AIDocument
from prefect_data_getters.stores.document_registry import register_document_type

@register_document_type("google_calendar_events")
class CalendarDocument(AIDocument):
    """Document type for Google Calendar events with calendar-specific functionality."""
    
    def __init__(self, page_content: str = "", metadata: dict = None, **kwargs):
        """
        Initialize CalendarDocument.
        
        Args:
            page_content: The main content of the calendar event
            metadata: Dictionary containing calendar event metadata
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(page_content=page_content, metadata=metadata or {}, **kwargs)
    
    def get_display_id(self) -> str:
        """Override to use event ID as display ID"""
        return self.event_id or "Unknown"
    
    # Calendar-specific properties
    @property
    def event_id(self) -> str:
        """Get the calendar event ID"""
        return self._get_metadata("event_id", "")
    
    @property
    def summary(self) -> str:
        """Get the event summary/title"""
        return self._get_metadata("summary", "")
    
    @property
    def description(self) -> str:
        """Get the event description"""
        return self._get_metadata("description", "")
    
    @property
    def location(self) -> str:
        """Get the event location"""
        return self._get_metadata("location", "")
    
    @property
    def organizer(self) -> str:
        """Get the event organizer"""
        return self._get_metadata("organizer", "")
    
    @property
    def attendees(self) -> str:
        """Get the event attendees"""
        return self._get_metadata("attendees", "")
    
    @property
    def start_time(self) -> str:
        """Get the event start time"""
        return self._get_metadata("start", "")
    
    @property
    def end_time(self) -> str:
        """Get the event end time"""
        return self._get_metadata("end", "")
    
    @property
    def status(self) -> str:
        """Get the event status"""
        return self._get_metadata("status", "")
    
    @property
    def event_type(self) -> str:
        """Get the event type"""
        return self._get_metadata("eventType", "")
    
    def __str__(self):
        """String representation using base formatter"""
        return self._format_document_string({
            "Event ID": self.event_id,
            "Summary": self.summary,
            "Description": self.description,
            "Location": self.location,
            "Organizer": self.organizer,
            "Attendees": self.attendees,
            "Start": self.start_time,
            "End": self.end_time,
            "Status": self.status,
            "Type": self.event_type
        })