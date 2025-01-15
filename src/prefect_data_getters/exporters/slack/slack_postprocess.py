import json
import os
from datetime import datetime
from langchain_chroma import Chroma
from langchain.schema import Document
from collections import defaultdict
import glob
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_community.vectorstores.utils import filter_complex_metadata


backup_dir = "/home/dusty/workspace/omnidian/slack-export/20240925-181512-slack_export"

# =======================
#  Asynchronous JSON Load
# =======================
def load_json_file(filepath):
    with open(filepath, mode='r') as file:
        contents = file.read()
        return json.loads(contents)

# ============================
#  Load Slack Data Asynchronously
# ============================
def load_slack_data():
    users = load_json_file(os.path.join(backup_dir,'users.json'))
    channels = load_json_file(os.path.join(backup_dir,'channels.json'))
    return users, channels

# ============================
#  Replace User Mentions
# ============================
def replace_user_mentions(text, user_map):
    if("<" in text):
        for user_id, real_name in user_map.items():
            mention = f"<@{user_id}>"
            text = text.replace(mention, real_name)
    return text

# ============================
#  Process Slack Messages
# ============================
def process_slack_messages(messages, user_map, channel_name):
    processed_documents = []
    for message in messages:
        text = replace_user_mentions(message['text'], user_map)

        # Dynamically extend metadata with all fields from message except 'text' and 'blocks'
        metadata = {key: value for key, value in message.items() if key not in ['text', 'blocks']}
        reaction_count = 0
        try:
            for r in metadata.get("reactions"):
                reaction_count += r.get("count")
        except:
            pass

        # Add additional metadata for user and channel information
        metadata.update({
            "type": "slack",
            "user": user_map.get(message.get("user"), None),  
            "channel": channel_name if channel_name else None,
            "reaction_count": reaction_count,
        })

        # specific date time fields
        for k in ["ts", "latest_reply", "thread_ts"]:
            try:
                metadata.update({
                    k: float(metadata[k]) if metadata[k] else None,
                    f"{k}_datetime": datetime.fromtimestamp(float(metadata[k])) if metadata[k] else None

                })
            except:
                print(f"Slack: could not process {k} from {metadata}")

        #unique id
        id = f"{channel_name}_{message.get('ts')}"
        if text is not None and len(text) > 0:
            document = Document(id = id, page_content=text, metadata=metadata)
            # document.id = id
            processed_documents.append(document)
    return filter_complex_metadata(processed_documents)


# Get files to process
def get_channel_directories(base_dir) -> list: 
    print(base_dir)
    ret = list()
    for d in os.listdir(base_dir):
        dd =os.path.join(base_dir,d)
        if(os.path.isdir(dd)):
            e = (dd, d)
            ret.append(e)
    return ret



# ============================
#  Main Program Logic
# ============================
def postprocess(backup_dir):
    
    # Load metadata asynchronously
    users, channels = load_slack_data()

    # Build mappings
    user_map = defaultdict(lambda: "Unknown", {user['id']: user['profile']['real_name'] for user in users})
    channel_map = defaultdict(lambda: "Unknown", {channel['id']: channel['name'] for channel in channels})
    
    num_docs = 0
    processed_documents = []
    print(f"in main: {backup_dir}", flush=True)
    for d in get_channel_directories(backup_dir):
        channel_name = d[1]

        json_files = glob.glob(os.path.join(d[0], "*.json"))
        for jf in json_files:
            messages = load_json_file(jf)

            # Process messages and enrich them with metadata
            processed_documents.extend(process_slack_messages(messages, user_map, channel_name))
            num_docs += len(processed_documents)
    return processed_documents

