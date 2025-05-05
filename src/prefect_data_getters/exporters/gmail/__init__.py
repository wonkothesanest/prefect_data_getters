import base64
from typing import List
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain.schema import Document
from datetime import datetime, timedelta

import prefect
from prefect_data_getters.utilities import parse_date
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import pickle
from email import message_from_bytes
from tenacity import retry, stop_after_attempt, wait_fixed

# Define the scope for read-only Gmail access
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send"
]

def authenticate_gmail():
    """
    Authenticates with the Gmail API using OAuth.
    Credentials are stored in a pickle file for reuse.
    """
    creds = None
    token_path = "secrets/gmail_token.pickle"
    creds_path = "secrets/google_app_creds.json"
    
    # Load saved credentials if they exist
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)
    
    # If there are no valid credentials available, let the user log in.
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except Exception as e:
            print(f"Error refreshing credentials: {e}")
            creds = None
        finally:
            if(creds is None):
                # If there are no (valid) credentials available, let the user log in.
                print("No valid credentials found. Please log in.")
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(f"Credentials file not found: {creds_path}")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=8080, access_type='offline')
        
        # Save the credentials for the next run
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
    
    return creds

def _get_gmail_service():
    """
    Returns an authenticated Gmail service.
    """
    creds = authenticate_gmail()
    service = build('gmail', 'v1', credentials=creds)
    return service

def _before_sleep(retry_state):
    # This function is called before each retry sleep.
    # You can access the exception from the previous attempt with retry_state.outcome.exception()
    exception = retry_state.outcome.exception()
    print(f"Retrying because of exception: {exception}")

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), before_sleep=_before_sleep)
def _get_message_list(service, query: str, next_page_token=None, maxResults=None):
    return service.users().messages().list(userId='me', q=query, pageToken=next_page_token, maxResults=maxResults).execute()

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), before_sleep=_before_sleep)
def _get_message(service, msg_id):
    return service.users().messages().get(userId="me", id=msg_id, format='raw').execute()

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), before_sleep=_before_sleep)
def _get_labels(service):
    return service.users().labels().list(userId='me').execute()

GMAIL_LABELS = None

def _get_label_mapping(service):
    """
    Get a mapping from label IDs to label names.
    """
    global GMAIL_LABELS
    if(GMAIL_LABELS is not None):
        return GMAIL_LABELS
    response = _get_labels(service)
    labels = response.get('labels', [])
    label_mapping = {label['id']: label['name'] for label in labels}
    GMAIL_LABELS = label_mapping
    return label_mapping

def get_labels():
    return _get_label_mapping(_get_gmail_service())

def _reset_labels():
    """
    Reset the cached label mapping.
    """
    global GMAIL_LABELS
    GMAIL_LABELS = None

def get_messages_by_query(query: str = "", maxResults=None):
    service = _get_gmail_service()
    label_mapping = _get_label_mapping(service)
    messages = []
    next_page_token = None

    while True:
        response = _get_message_list(service, query, next_page_token, maxResults=maxResults)
        if 'messages' in response:
            messages.extend(response['messages'])
        next_page_token = response.get('nextPageToken')
        if not next_page_token or (maxResults is not None and len(messages) >= maxResults):
            break

    full_messages = []
    for msg in messages:
        msg_id = msg['id']
        message = _get_message(service, msg_id)
        msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
        mime_msg = message_from_bytes(msg_str)
        mime_msg.add_header("Google-ID", msg_id)
        mime_msg.add_header("Google-Thread-ID", msg['threadId'])
        mime_msg.add_header("Labels", ','.join([label_mapping.get(label_id, label_id) for label_id in message.get('labelIds', [])]))

        full_messages.append(mime_msg)

    return full_messages

def get_messages(days_ago):
    """
    Get all messages from the past given number of days.
    """
    query_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y/%m/%d')
    bad_labels = ['useless', 'not-important', 'tools-calendar', 'tools-alarms', 'tools-bitbucket']
    bad_labels_query = ' AND '.join([f"NOT label:{label}" for label in bad_labels])
    query = f"after:{query_date} AND {bad_labels_query} AND NOT in:spam AND NOT in:trash"
    return get_messages_by_query(query)

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
    """
    Extract metadata from the Gmail message.
    """
    metadata = {}
    headers = ['Message-ID', 'From', 'To', 'Cc', 'Bcc', 'Subject', 'Date', 'Reply-To', 'In-Reply-To', 'References', 'Google-ID', 'Google-Thread-ID', 'Labels']
    for header in headers:
        value = message.get(header)
        if value:
            stripped_value = str(value).strip()
            if header == 'Date':
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
        id=metadata['google-id'], 
        page_content=body,
        metadata=metadata
    )
    return document

def apply_labels_to_email(email_id: str, 
                          category_labels: List[str] = [], 
                          team_labels: List[str] = [],  
                          project_labels: List[str] = [],  
                          sytems_labels: List[str] = []):
    """Apply suggested labels to the processed email."""
    service = _get_gmail_service()  # Get the Gmail service
    created_labels = []
    not_new_labels = []
    all = {"Cats": category_labels, "Teams": team_labels, "Projects": project_labels, "Systems": sytems_labels}
    for label_type, label_list in all.items():
        existing_labels = get_labels()  # Get existing labels from Gmail
        category_labels = _smoosh_labels_together(label_list, label_type=label_type, existing_labels=existing_labels)
        for label in label_list:
            if not any(value.endswith(f"/{label_type}/{label}") for value in existing_labels.values()):
                # Create new label if it doesn't exist
                try:
                    new_label = service.users().labels().create(userId='me', body={'name': f'AI/{label_type}/{label}'}).execute()
                    created_labels.append(new_label['id'])
                    _reset_labels()
                except Exception as e:
                    continue
            else:            
                for key, value in existing_labels.items():
                    if value.endswith(f"{label_type}/{label}"):
                        not_new_labels.append(key)
                        break

    # Apply labels to the email
    label_ids = not_new_labels + created_labels

    if(label_ids):
        service.users().messages().modify(userId='me', id=email_id, body={'addLabelIds': label_ids}).execute()


from prefect_data_getters.utilities.similarity import calculate_similarity
def _smoosh_labels_together(suggested_labels, label_type, existing_labels, threshold=0.60):
    """Update labels based on similarity scores."""
    if not suggested_labels:
        return []
    existing_label_strings = list(existing_labels.values())
    updated_labels = []
    existing_label_strings = [label.replace(f"AI/{label_type}/", "") for label in existing_label_strings if label.startswith(f"AI/{label_type}/")]
    if not existing_label_strings:
        return suggested_labels
    for label in suggested_labels:

        similarities = calculate_similarity(existing_label_strings, label)
        if any(result['similarity_score'] > threshold for result in similarities):
            # Replace with the most similar existing label
            updated_labels.append(next(result['value'] for result in similarities if result['similarity_score'] > threshold))
        else:
            updated_labels.append(label)

    return updated_labels

if __name__ == "__main__":
    # Example usage
    apply_labels_to_email(
        email_id="19663a0288712d11",
        category_labels=["Project Updates", "Client Communication"],
        team_labels=["Data Engineering", "Onboarding Team"],
        project_labels=[],
        sytems_labels=["Asana", "Jira"]
    )
