import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from time import sleep
from urllib.parse import urlparse
import requests
from pick import pick
from prefect_data_getters.utilities.constants import SCRATCH_BASE_DIR


from .slacker_module import Slacker, Conversations

def getReplies(slack, channelId, timestamp, oldestTimestamp, pageSize=1000):
    conversationObject = slack.conversations
    messages = []
    lastTimestamp = None
    lastTimestampFromPreviousIteration = lastTimestamp

    while True:
        try:
            response = conversationObject.replies(
                channel=channelId,
                ts=timestamp,
                latest=lastTimestamp,
                oldest=oldestTimestamp,
                limit=pageSize,
            ).body
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retryInSeconds = int(e.response.headers["Retry-After"])
                print("Rate limit hit. Retrying in {0} second{1}.".format(retryInSeconds, "s" if retryInSeconds > 1 else ""))
                sleep(retryInSeconds + 1)

                response = conversationObject.replies(
                    channel=channelId,
                    ts=timestamp,
                    latest=lastTimestamp,
                    oldest=oldestTimestamp,
                    limit=pageSize,
                ).body

        messages.extend(response["messages"])

        if response["has_more"] == True:
            sys.stdout.write(".")
            sys.stdout.flush()
            # sleep(1.3)  # Respect the Slack API rate limit

            lastTimestamp = messages[-1]['ts']  # -1 means last element in a list
            minTimestamp = None

            if lastTimestamp == lastTimestampFromPreviousIteration:
                # Then we might be in an infinite loop,
                # because lastTimestamp is supposed to be decreasing.
                # Try harder: maybe we want messages[-2]['ts']?

                minTimestamp = float(lastTimestamp)
                for m in messages:
                    if minTimestamp > float(m['ts']):
                        minTimestamp = float(m['ts'])

                if minTimestamp == lastTimestamp:
                    print("warning: lastTimestamp is not changing.  infinite loop?")
                lastTimestamp = minTimestamp

            lastTimestampFromPreviousIteration = lastTimestamp

        else:
            break

    if lastTimestamp != None:
        print("")

    messages.sort(key=lambda message: message["ts"])

    # Obtaining replies also gives us the first message in the the thread
    # (which we don't want) -- after sorting, our first message with the be the
    # first in the list of all messages, so we remove the head of the list
    assert messages[0]["ts"] == timestamp, "unexpected start of thread"
    messages = messages[1:]

    return messages

def getHistory(slack, pageableObject, channelId, oldestTimestamp, pageSize=1000):
    messages = []
    lastTimestamp = None
    lastTimestampFromPreviousIteration = lastTimestamp

    while True:
        try:
            if isinstance(pageableObject, Conversations):
                response = pageableObject.history(
                    channel=channelId,
                    latest=lastTimestamp,
                    oldest=oldestTimestamp,
                    limit=pageSize
                ).body
            else:
                response = pageableObject.history(
                    channel=channelId,
                    latest=lastTimestamp,
                    oldest=oldestTimestamp,
                    count=pageSize
                ).body
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retryInSeconds = int(e.response.headers['Retry-After'])
                print("Rate limit hit. Retrying in {0} second{1}.".format(retryInSeconds, "s" if retryInSeconds > 1 else ""))
                sleep(retryInSeconds + 1)
                if isinstance(pageableObject, Conversations):
                    response = pageableObject.history(
                        channel=channelId,
                        latest=lastTimestamp,
                        oldest=oldestTimestamp,
                        limit=pageSize
                    ).body
                else:
                    response = pageableObject.history(
                        channel=channelId,
                        latest=lastTimestamp,
                        oldest=oldestTimestamp,
                        count=pageSize
                    ).body

        messages.extend(response['messages'])

        # Grab all replies
        for message in response["messages"]:
            if "thread_ts" in message:
                # sleep(0.5)  # INSERT LIMIT
                messages.extend(getReplies(slack, channelId, message["thread_ts"], oldestTimestamp, pageSize))

        if (response['has_more'] == True):
            sys.stdout.write("*")
            sys.stdout.flush()
            # sleep(1.3)  # Respect the Slack API rate limit

            lastTimestamp = messages[-1]['ts']  # -1 means last element in a list
            minTimestamp = None

            if lastTimestamp == lastTimestampFromPreviousIteration:
                # Then we might be in an infinite loop,
                # because lastTimestamp is supposed to be decreasing.
                # Try harder: maybe we want messages[-2]['ts']?

                minTimestamp = float(lastTimestamp)
                for m in messages:
                    if minTimestamp > float(m['ts']):
                        minTimestamp = float(m['ts'])

                if minTimestamp == lastTimestamp:
                    print("warning: lastTimestamp is not changing.  infinite loop?")
                lastTimestamp = minTimestamp

            lastTimestampFromPreviousIteration = lastTimestamp

        else:
            break

    if lastTimestamp != None:
        print("")

    messages.sort(key=lambda message: message['ts'])

    return messages

def mkdir(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)

# create datetime object from slack timestamp ('ts') string
def parseTimeStamp(timeStamp):
    if '.' in timeStamp:
        t_list = timeStamp.split('.')
        if len(t_list) != 2:
            raise ValueError('Invalid time stamp')
        else:
            return datetime.utcfromtimestamp(float(t_list[0]))

# move channel files from old directory to one with new channel name
def channelRename(oldRoomName, newRoomName):
    # check if any files need to be moved
    if not os.path.isdir(oldRoomName):
        return
    mkdir(newRoomName)
    for fileName in os.listdir(oldRoomName):
        shutil.move(os.path.join(oldRoomName, fileName), newRoomName)
    os.rmdir(oldRoomName)

def writeMessageFile(fileName, messages):
    directory = os.path.dirname(fileName)

    # if there's no data to write to the file, return
    if not messages:
        return

    if not os.path.isdir(directory):
        mkdir(directory)

    with open(fileName, 'w') as outFile:
        json.dump(messages, outFile, indent=4)

# parse messages by date
def parseMessages(roomDir, messages, roomType):
    nameChangeFlag = roomType + "_name"

    currentFileDate = ''
    currentMessages = []
    for message in messages:
        # first store the date of the next message
        ts = parseTimeStamp(message['ts'])
        fileDate = '{:%Y-%m-%d}'.format(ts)

        # if it's on a different day, write out the previous day's messages
        if fileDate != currentFileDate:
            outFileName = '{room}/{file}.json'.format(room=roomDir, file=currentFileDate)
            writeMessageFile(outFileName, currentMessages)
            currentFileDate = fileDate
            currentMessages = []

        # check if current message is a name change
        # dms won't have name change events
        if roomType != "im" and ('subtype' in message) and message['subtype'] == nameChangeFlag:
            roomDir = message['name']
            oldRoomPath = message['old_name']
            newRoomPath = roomDir
            channelRename(oldRoomPath, newRoomPath)

        currentMessages.append(message)
    outFileName = '{room}/{file}.json'.format(room=roomDir, file=currentFileDate)
    writeMessageFile(outFileName, currentMessages)

def filterConversationsByName(channelsOrGroups, channelOrGroupNames):
    return [conversation for conversation in channelsOrGroups if conversation['name'] in channelOrGroupNames]

def promptForPublicChannels(channels):
    channelNames = [channel['name'] for channel in channels]
    selectedChannels = pick(channelNames, 'Select the Public Channels you want to export:', multi_select=True)
    return [channels[index] for channelName, index in selectedChannels]

# fetch and write history for all public channels
def fetchPublicChannels(slack, channels, dryRun, oldestTimestamp):
    print("Fetching", len(channels), "public channels")
    if dryRun:
        print("Public Channels selected for export:")
        for channel in channels:
            print(channel['name'])
        print()
        return

    for channel in channels:
        channelDir = channel['name']
        print("Fetching history for Public Channel: {0}".format(channelDir))
        try:
            mkdir(channelDir)
        except NotADirectoryError:
            # Failed creating directory, probably because the name is not a valid
            # Windows directory name (like "com4"). Adding a prefix to try to work-around
            # that.
            channelDir = ("c-" + channel['name'])
            mkdir(channelDir)
        messages = getHistory(slack, slack.conversations, channel['id'], oldestTimestamp)
        parseMessages(channelDir, messages, 'channel')

# write channels.json file
def dumpChannelFile(channels, groups, dms):
    print("Making channels file")

    private = []
    mpim = []

    for group in groups:
        if group['is_mpim']:
            mpim.append(group)
            continue
        private.append(group)

    # slack viewer wants DMs to have a members list, not sure why but doing as they expect
    for dm in dms:
        dm['members'] = [dm['user']]

    # We will be overwriting this file on each run.
    with open('channels.json', 'w') as outFile:
        json.dump(channels, outFile, indent=4)
    with open('groups.json', 'w') as outFile:
        json.dump(private, outFile, indent=4)
    with open('mpims.json', 'w') as outFile:
        json.dump(mpim, outFile, indent=4)
    with open('dms.json', 'w') as outFile:
        json.dump(dms, outFile, indent=4)

def filterDirectMessagesByUserNameOrId(dms, userNamesOrIds, userIdsByName):
    userIds = [userIdsByName.get(userNameOrId, userNameOrId) for userNameOrId in userNamesOrIds]
    return [dm for dm in dms if dm['user'] in userIds]

def promptForDirectMessages(dms, userNamesById):
    dmNames = [userNamesById.get(dm['user'], dm['user'] + " (name unknown)") for dm in dms]
    selectedDms = pick(dmNames, 'Select the 1:1 DMs you want to export:', multi_select=True)
    return [dms[index] for dmName, index in selectedDms]

# fetch and write history for all direct message conversations
def fetchDirectMessages(slack, dms, dryRun, userNamesById, oldestTimestamp):
    print("Fetching", len(dms), "1:1 DMs")
    if dryRun:
        print("1:1 DMs selected for export:")
        for dm in dms:
            print(userNamesById.get(dm['user'], dm['user'] + " (name unknown)"))
        print()
        return

    for dm in dms:
        name = userNamesById.get(dm['user'], dm['user'] + " (name unknown)")
        print("Fetching 1:1 DMs with {0}".format(name))
        dmId = dm['id']
        mkdir(dmId)
        messages = getHistory(slack, slack.conversations, dm['id'], oldestTimestamp)
        parseMessages(dmId, messages, "im")

def promptForGroups(groups):
    groupNames = [group['name'] for group in groups]
    selectedGroups = pick(groupNames, 'Select the Private Channels and Group DMs you want to export:', multi_select=True)
    return [groups[index] for groupName, index in selectedGroups]

# fetch and write history for specific private channel
def fetchGroups(slack, groups, dryRun, oldestTimestamp):
    print("Fetching", len(groups), "Private Channels and Group DMs")
    if dryRun:
        print("Private Channels and Group DMs selected for export:")
        for group in groups:
            print(group['name'])
        print()
        return

    for group in groups:
        groupDir = group['name']
        mkdir(groupDir)
        messages = []
        print("Fetching history for Private Channel / Group DM: {0}".format(group['name']))
        messages = getHistory(slack, slack.conversations, group['id'], oldestTimestamp)
        parseMessages(groupDir, messages, 'group')

def process_group(slack, group, oldestTimestamp):
    groupDir = group['name']
    os.mkdir(groupDir)
    print(f"Fetching history for Private Channel / Group DM: {groupDir}", flush=True)
    messages = getHistory(slack, slack.conversations, group['id'], oldestTimestamp)
    parseMessages(groupDir, messages, 'group')

# fetch all users for the channel and return a map userId -> userName
def getUserMap(users):
    userNamesById = {}
    userIdsByName = {}
    for user in users:
        userNamesById[user['id']] = user['name']
        userIdsByName[user['name']] = user['id']
    return userNamesById, userIdsByName

# stores json of user info
def dumpUserFile(users):
    # write to user file, any existing file needs to be overwritten.
    with open("users.json", 'w') as userFile:
        json.dump(users, userFile, indent=4)

# get basic info about the slack channel to ensure the authentication token works
def doTestAuth(slack):
    testAuth = slack.auth.test().body
    teamName = testAuth['team']
    currentUser = testAuth['user']
    print("Successfully authenticated for team {0} and user {1} ".format(teamName, currentUser))
    return testAuth


def bootstrapKeyValues(slack, suppliedChannels=None, suppliedGroups=None, oldestTimestamp=None):
    users = []
    channels = []
    groups = []
    dms = []

    # Fetch users
    users_list = slack.users.list(limit=200).body
    users.extend(users_list['members'])
    while users_list.get('response_metadata', {}).get('next_cursor'):
        cursor = users_list['response_metadata']['next_cursor']
        # sleep(1)
        users_list = slack.users.list(limit=200, cursor=cursor).body
        users.extend(users_list['members'])

    print("Found {0} Users".format(len(users)))
    # sleep(1)

    # Fetch channels
    channels_list = slack.conversations.list(limit=200, types=('public_channel')).body
    channels.extend(channels_list['channels'])
    while channels_list.get('response_metadata', {}).get('next_cursor'):
        cursor = channels_list['response_metadata']['next_cursor']
        # sleep(1)
        channels_list = slack.conversations.list(limit=200, types=('public_channel'), cursor=cursor).body
        channels.extend(channels_list['channels'])

    if suppliedChannels is not None:
        channels = list(filter(lambda obj: obj["name"] in suppliedChannels, channels))
    # else:
    #     channels = list(filter(lambda obj: obj["is_member"], channels))
    
    print("Found {0} Public Channels".format(len(channels)))

    # Fetch groups
    groups_list = slack.conversations.list(limit=200, types=('private_channel', 'mpim')).body
    groups.extend(groups_list['channels'])
    while groups_list.get('response_metadata', {}).get('next_cursor'):
        cursor = groups_list['response_metadata']['next_cursor']
        # sleep(1)
        groups_list = slack.conversations.list(limit=200, types=('private_channel', 'mpim'), cursor=cursor).body
        groups.extend(groups_list['channels'])

    if suppliedGroups is not None:
        groups = list(filter(lambda obj: obj["name"] in suppliedGroups, groups))
    else:
        # If a group chat we have a cut off of when the group was updated if the number of members is 4 or more
        # The thinking behind this is every time we update we look at > 1000 dead stale chats. 1:1s stay alive for a long time
        # big groups get turned into channels.
        groups = list(filter(
            lambda obj: (
                obj["is_member"] and (
                    (not obj.get("is_mpim", False)) or
                    (obj["is_mpim"] and obj["num_members"] > 3 and obj["updated"] > oldestTimestamp*1000 - timedelta(days=31).total_seconds()*1000) or
                    (obj["is_mpim"] and obj["num_members"] <= 3)
                )
            ),
            groups
        ))
    print("Found {0} Private Channels or Group DMs".format(len(groups)))

    # Fetch DMs
    dms_list = slack.conversations.list(limit=200, types=('im')).body
    dms.extend(dms_list['channels'])
    while dms_list.get('response_metadata', {}).get('next_cursor'):
        cursor = dms_list['response_metadata']['next_cursor']
        # sleep(1)
        dms_list = slack.conversations.list(limit=200, types=('im'), cursor=cursor).body
        dms.extend(dms_list['channels'])

    print("Found {0} 1:1 DM conversations\n".format(len(dms)))
    # sleep(1)

    return users, channels, groups, dms

def selectConversations(allConversations, commandLineArg, filter, prompt, args):
    if args.exclude_archived:
        allConversations = [conv for conv in allConversations if not conv.get("is_archived", False)]
    if isinstance(commandLineArg, list) and len(commandLineArg) > 0:
        return filter(allConversations, commandLineArg)
    elif commandLineArg != None or not anyConversationsSpecified(args):
        if args.prompt:
            return prompt(allConversations)
        else:
            return allConversations
    else:
        return []

# Returns true if any conversations were specified on the command line
def anyConversationsSpecified(args):
    return args.public_channels != None or args.groups != None or args.direct_messages != None

# This method is used in order to create an empty Channel if you do not export public channels
# otherwise, the viewer will error and not show the root screen.
def dumpDummyChannel(channels):
    if len(channels) == 0:
        return
    channelName = channels[0]['name']
    mkdir(channelName)
    fileDate = '{:%Y-%m-%d}'.format(datetime.today())
    outFileName = '{room}/{file}.json'.format(room=channelName, file=fileDate)
    writeMessageFile(outFileName, [])

def downloadFiles(slack, token, cookie_header=None):
    """
    Iterate through all json files, downloads files stored on files.slack.com and replaces the link with a local one
    """
    print("Starting to download files")
    for root, subdirs, files in os.walk("."):
        for filename in files:
            if not filename.endswith('.json'):
                continue
            filePath = os.path.join(root, filename)
            data = []
            with open(filePath) as inFile:
                data = json.load(inFile)
                for msg in data:
                    for slackFile in msg.get("files", []):
                        # Skip deleted files
                        if slackFile.get("mode") == "tombstone":
                            continue

                        for key, value in slackFile.items():
                            # Find all entries referring to files on files.slack.com
                            if not isinstance(value, str) or not value.startswith("https://files.slack.com/"):
                                continue

                            url = urlparse(value)

                            localFile = os.path.join("../files.slack.com", url.path[1:])  # Need to discard first "/" in URL
                            print("Downloading %s, saving to %s" % (url.geturl(), localFile))

                            # Create folder structure
                            os.makedirs(os.path.dirname(localFile), exist_ok=True)

                            # Replace URL in data - suitable for use with slack-export-viewer if files.slack.com is linked
                            slackFile[key] = "/static/files.slack.com%s" % url.path

                            # Check if file already downloaded, with a non-zero size
                            if os.path.exists(localFile) and (os.path.getsize(localFile) > 0):
                                print("Skipping already downloaded file: %s" % localFile)
                                continue

                            # Download files
                            headers = {"Authorization": f"Bearer {token}",
                                       **cookie_header}
                            r = requests.get(url.geturl(), headers=headers)
                            try:
                                open(localFile, 'wb').write(r.content)
                            except FileNotFoundError:
                                print("File writing error-still all broken")
                                continue

            # Save updated data to json file
            with open(filePath, "w") as outFile:
                json.dump(data, outFile, indent=4, sort_keys=True)

            print("Replaced all files in %s" % filePath)

def finalize(outputDirectory, zipName):
    os.chdir('../../')
    if zipName:
        shutil.make_archive(zipName, 'zip', outputDirectory, None)
        shutil.rmtree(outputDirectory)
    return os.path.abspath(outputDirectory)

def do_backup(token, start_from_timestamp=None, public_channels=None, groups=None, direct_messages=None,
              prompt=False, dry_run=False, zip_name=None, download_slack_files=False,
              exclude_archived=False, exclude_non_member=False, cookie=None):

    oldestTimestamp = 0
    if start_from_timestamp:
        oldestTimestamp = start_from_timestamp

    cookie_header = {'cookie': cookie} if cookie else {}
    slack = Slacker(headers=cookie_header, token=token)
    testAuth = doTestAuth(slack)
    tokenOwnerId = testAuth['user_id']

    # Mock args
    class Args:
        pass

    args = Args()
    args.public_channels = public_channels
    args.groups = groups
    args.direct_messages = direct_messages
    args.prompt = prompt
    args.dry_run = dry_run
    args.download_slack_files = download_slack_files
    args.exclude_archived = exclude_archived
    args.exclude_non_member = exclude_non_member

    users, channels, groups_list, dms = bootstrapKeyValues(slack, public_channels, groups, oldestTimestamp)
    userNamesById, userIdsByName = getUserMap(users)

    dryRun = dry_run
    zipName = zip_name

    outputDirectory = os.path.join(SCRATCH_BASE_DIR, "{0}-slack_export".format(datetime.today().strftime("%Y%m%d-%H%M%S")))
    mkdir(outputDirectory)
    os.chdir(outputDirectory)

    if not dryRun:
        dumpUserFile(users)
        dumpChannelFile(channels, groups_list, dms)

    selectedChannels = selectConversations(
        channels,
        args.public_channels,
        filterConversationsByName,
        promptForPublicChannels,
        args)
    if args.exclude_non_member:
        selectedChannels = [channel for channel in selectedChannels if channel.get("is_member", False)]

    selectedGroups = selectConversations(
        groups_list,
        args.groups,
        filterConversationsByName,
        promptForGroups,
        args)

    selectedDms = selectConversations(
        dms,
        args.direct_messages,
        lambda dms, userNamesOrIds: filterDirectMessagesByUserNameOrId(dms, userNamesOrIds, userIdsByName),
        lambda dms: promptForDirectMessages(dms, userNamesById),
        args)

    if len(selectedChannels) > 0:
        fetchPublicChannels(slack, selectedChannels, dryRun, oldestTimestamp)

    if len(selectedGroups) > 0:
        if len(selectedChannels) == 0:
            dumpDummyChannel(channels)
        fetchGroups(slack, selectedGroups, dryRun, oldestTimestamp)

    if len(selectedDms) > 0:
        fetchDirectMessages(slack, selectedDms, dryRun, userNamesById, oldestTimestamp)

    if args.download_slack_files:
        downloadFiles(slack, token=token, cookie_header=cookie_header)

    output_path = finalize(outputDirectory, zipName)
    return output_path
