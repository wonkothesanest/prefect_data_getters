from prefect import flow, task
from prefect.blocks.system import Secret
from prefect_data_getters.utilities.prefect import get_last_successful_flow_run_timestamp
from datetime import datetime, timedelta
from typing import List
from langchain.schema import Document
from prefect_data_getters.stores.document_types.slack_document import SlackMessageDocument
from prefect_data_getters.exporters.slack_exporter import SlackExporter
from prefect_data_getters.utilities import constants as C
from prefect.artifacts import create_markdown_artifact

@task
def fetch_slack_messages(token: str, cookie: str = None, days_ago: int = 7, channels: List[str] = None) -> List[dict]:
    """Fetch raw Slack message data using the new SlackExporter."""
    config = {"token": token, "cookie": cookie}
    slack_exporter = SlackExporter(config)
    slack_docs = slack_exporter.export(channels=channels, days_ago=days_ago)
    return list(slack_docs)

@task
def process_messages_to_documents(raw_messages: List[dict], cookie: str = None) -> List[Document]:
    """Process raw Slack data into Document objects."""
    # We need to pass the token in config for the SlackExporter to work properly
    token = Secret.load("slack-token").get()
    config = {"token": token}
    if cookie:
        config["cookie"] = cookie
    slack_exporter = SlackExporter(config)
    documents = list(slack_exporter.process(iter(raw_messages)))
    return documents

@task
def store_documents_in_vectorstore(documents: List[Document]):
    """Store Slack documents in vector store."""
    if documents:
        SlackMessageDocument.save_documents(
            docs=documents,
            store_name="slack_messages",
            also_store_vectors=True
        )

@flow(name="slack-backup-flow", log_prints=True, timeout_seconds=3600)
def slack_backup_flow(first_date: str | None = None, public_channel: list[str] | None = None):
    """
    Main Prefect flow to perform the Slack backup and process the message files.
    """
    # Retrieve the Slack API token from Prefect variables
    token = Secret.load("slack-token").get()

    if not token:
        raise ValueError("Slack API token is not set. Please set the 'slack-token' Prefect variable.")

    # Retrieve the Slack cookie from Prefect secrets (optional for enhanced authentication)
    cookie = Secret.load("slack-cookie").get()

    # Calculate the date range for fetching messages
    last_successful_timestamp = None
    if first_date is not None:
        try:
            last_successful_timestamp = datetime.fromisoformat(first_date).timestamp()
            print(f"Using user supplied first date: {first_date} as {last_successful_timestamp} timestamp")
        except:
            print(f"parsing first date did not work {first_date}.")
    
    if last_successful_timestamp is None:
        last_successful_timestamp = get_last_successful_flow_run_timestamp("slack-backup-flow")
        if last_successful_timestamp is not None:
            last_successful_timestamp = last_successful_timestamp - timedelta(days=1).total_seconds()
        else:
            last_successful_timestamp = (datetime.now() - timedelta(days=60)).timestamp()
            print(f"Using default first date: {last_successful_timestamp} timestamp")

    # Calculate days_ago from timestamp
    days_ago = int((datetime.now().timestamp() - last_successful_timestamp) / (24 * 3600))
    
    print(f"Start time: {last_successful_timestamp}. Now is {datetime.now().timestamp()}")
    print(f"Fetching messages from {days_ago} days ago")
    create_markdown_artifact(f"Start Time: {datetime.fromtimestamp(last_successful_timestamp)}\nEnd Time: {datetime.now()}")

    # Step 1: Fetch raw Slack messages
    raw_messages = fetch_slack_messages(token, cookie=cookie, days_ago=days_ago, channels=public_channel)
    
    # Step 2: Process messages into Document objects
    documents = process_messages_to_documents(raw_messages, cookie=cookie)
    
    create_markdown_artifact(f"Number of slack messages processed: {len(documents)}", key="num-slack-message", description=f"The number of slack messages processed is {len(documents)}")
    print(f"Processing {len(documents)} number of slack messages")

    # Step 3: Store documents in vector store
    store_documents_in_vectorstore(documents)

    print(f"Backup and processing completed. Processed {len(documents)} messages.")



if __name__ == '__main__':
    # deployment = slack_backup_flow.serve(
    #     name="slack-backup-deployment",
    #     # work_pool_name="default",
    # )
    # In order to deploy you have to create an image, stop going down other paths.
    # slack_backup_flow.deploy(
    #     name="slack-backup-deployment",
    #     work_pool_name="default",)
    slack_backup_flow()
