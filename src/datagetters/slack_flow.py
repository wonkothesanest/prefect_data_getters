from prefect import flow, task
from prefect.variables import Variable
from prefect.blocks.system import Secret
from exporters import add_default_metadata
from utilities.prefect import get_last_successful_flow_run_timestamp
from datetime import datetime, timedelta
from glob import glob
from exporters.slack.slack_backup import do_backup  # Adjust the import as needed
import exporters.slack.slack_postprocess as slack_postprocess
from stores.vectorstore import ESVectorStore, batch_process_and_store, get_embeddings_and_vectordb
import utilities.constants as C
from prefect.filesystems import LocalFileSystem
from  prefect.artifacts import create_markdown_artifact


@task
def perform_backup(token, start_timestamp=None, cookie=None):
    """
    Task to perform Slack backup using the do_backup function.
    """
    # return "/media/dusty/TB2/workspace/omnidian/prefect_data_getters/20241022-102918-slack_export"
    backup_directory = do_backup(
        token=token,
        start_from_timestamp=start_timestamp,
        cookie=cookie
    )
    return backup_directory


@task
def postprocess_json_files(backup_directory):
    """
    Task to process each .json file in the backup directory's subdirectories,
    adding "username", "full_name", and "channel_name" properties to each message.
    """
    return add_default_metadata(slack_postprocess.postprocess(backup_directory))
    

@task
def store_vector_db(messages, backupdir):
    (emb, vecdb) = get_embeddings_and_vectordb("slack_messages")
    batch_process_and_store(messages, vecdb, batch_size=40000)



    

@flow(name="slack-backup-flow",log_prints=True)
def slack_backup_flow():
    """
    Main Prefect flow to perform the Slack backup and process the message files.
    """
    # Retrieve the Slack API token and cookie from Prefect variables
    token = Secret.load("slack-token").get()
    cookie = Secret.load("slack-cookie").get()

    if not token:
        raise ValueError("Slack API token is not set. Please set the 'slack_api_token' Prefect variable.")
    if not cookie:
        raise ValueError("Slack cookie is not set. Please set the 'slack_cookie' Prefect variable.")

    # Optional parameters (adjust as needed)    
    # Get the last successful run timestamp
    last_successful_timestamp = get_last_successful_flow_run_timestamp("slack-backup-flow")


    # last_successful_timestamp = (datetime.now() - timedelta(days=60)).timestamp()
    print(f"Last timestamp successfully run {last_successful_timestamp}. Now is {datetime.now().timestamp()}")
    create_markdown_artifact(f"Start Time: {datetime.fromtimestamp(last_successful_timestamp)}\nEnd Time: {datetime.now()}")

    # Step 1: Perform the backup
    backup_directory = perform_backup(
        token=token,
        start_timestamp=last_successful_timestamp,
        cookie=cookie
    )
    # backup_directory = "/home/dusty/workspace/omnidian/scratch/20241029-133915-slack_export"

    # Step 3: Process each .json file to add properties to messages
    slack_messages = postprocess_json_files(backup_directory)
    create_markdown_artifact(f"Number of slack messages processed: {len(slack_messages)}", key="num-slack-message", description=f"The number of slack messages processed is {len(slack_messages)}")
    print(f"Processing {len(slack_messages)} number of slack messages")

    store_vector_db(slack_messages, C.VECTOR_STORE_DIR)

    print(f"Backup and processing completed. Files are stored in: {backup_directory}")



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