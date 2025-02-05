from typing import Literal


VECTOR_STORE_DIR = "/home/dusty/workspace/omnidian/vectorstores/"
DEPLOYMENT_STORE_DIR = "/home/dusty/workspace/omnidian/deployments/"
SCRATCH_BASE_DIR = "/home/dusty/workspace/omnidian/scratch"
# Define the path to the mbox file
MBOX_FILE_PATH = '/home/dusty/.thunderbird/NGBackups/' 
#TODO: Change this to be dynamic, for now this is a manual process.
SLAB_BACKUP_DIR = "/media/dusty/TB2/workspace/dusty/langchain-example/data/slab_docs/data"

DESIRED_DOCUMENT_CHARACTER_LENGTH = 5000

ES_URL = "http://localhost:9200"
data_stores = [
    {
        "name": "email_messages",
        "description": "A collection of email messages updated at regular frequency from Dusty Hagstrom's mail folders. The individual documents are emails sent to and from Dusty.",
    },
    {
        "name": "jira_issues",
        "description": "A collection of issues from the Jira project management tool, containing details about tasks, bugs, epics, and features being tracked.",
    },
    {
        "name": "slab_document_chunks",
        "description": "Chunks of documents sourced from Slab, an internal knowledge base platform, providing bite-sized information for easy retrieval. This contains all of the documentation from Omnidian as well as product planning documents and engineering tech specs and functional specifications",
    },
    {
        "name": "slab_documents",
        "description": "Complete documents from Slab that provide detailed information, guidelines, and internal documentation for team reference.  This contains all of the documentation from Omnidian as well as product planning documents and engineering tech specs and functional specifications.",
    },
    {
        "name": "slack_messages",
        "description": "Messages exchanged in Slack, capturing real-time communication and discussions among team members across different channels.",
    },
    {
        "name": "bitbucket_pull_requests",
        "description": "A list of pull requests performed at Omnidian and their comments and authors."
    }
]
ALL_INDEXES = [d["name"] for d in data_stores]
VECTOR_STORE_NAMES = Literal[
    "email_messages",
    "jira_issues",
    "slab_document_chunks",
    "slab_documents",
    "slack_messages",
    "bitbucket_pull_requests",
]