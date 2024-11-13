from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain.schema import Document
from datetime import datetime
from utilities import parse_date


def get_email_body(message) -> str:
    """Extracts the body from an email message."""
    if message.is_multipart():
        parts = []
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))
            # Skip attachments
            if content_disposition and 'attachment' in content_disposition:
                continue
            if content_type == 'text/plain':
                charset = part.get_content_charset()
                payload = part.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode(charset or 'utf-8', errors='replace'))
        return '\n'.join(parts)
    else:
        payload = message.get_payload(decode=True)
        charset = message.get_content_charset()
        if payload:
            return payload.decode(charset or 'utf-8', errors='replace')
    return ''

def get_metadata(message):
    
    # Extract metadata and strip whitespace/newlines
    metadata = {}
    message_id = message.get('Message-ID', None)
    if(message_id == None):
        raise(Exception("No message id!"))
    headers = ['Message-ID', 'From', 'To', 'Cc', 'Bcc', 'Subject', 'Date', 'Reply-To', 'In-Reply-To', 'References']
    for header in headers:
        value = message.get(header)
        if value:
            # Strip leading/trailing whitespace and newlines
            stripped_value = str(value).strip()
            if(header in ['Date']):
                try:
                    metadata[header.lower()] = parse_date(stripped_value)
                except:
                    pass
            else:
                metadata[header.lower()] = stripped_value

    return metadata


def process_message(message) -> Document:
    # Extract unique ID (use the message ID or assign a unique number)
    metadata = get_metadata(message)
    # Extract email body
    body = get_email_body(message)

    # Create Document object
    document = Document(
        id=metadata['message-id'] , 
        page_content=body,
        metadata=metadata
    )
    return document