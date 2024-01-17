import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from BotData import UserInfo, ReactionEvent, MessageEvent, EmbeddedFile, EmbeddedLink, Message, ProviderFunctionsBase
import logging
import asyncio
import threading
import UserProfile

# Check for slack token and if not present, call localdata to load it
if not os.environ.get("SLACK_BOT_TOKEN"):
    import LocalData
    LocalData.load_local_data()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Function to start and run the event loop
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Create a new loop and run it in a separate thread
new_loop = asyncio.new_event_loop()
t = threading.Thread(target=start_loop, args=(new_loop,))
t.start()


REACTION_DB = {
    'looking': 'eyes',
    'thinking':'brain',
    'thumbs_up':'thumbsup',
    'thumbs_down':'thumbsdown',
    'green_check':'white_check_mark',
    'process_image':'frame_with_picture',
    'phase_context_gathering': 'eyes',
    'phase_enrichment':'frame_with_picture',
    'phase_processing': 'brain',
    'phase_validation': 'mag',
    'phase_request_complete': 'white_check_mark',
    'phase_request_failed': 'x'
}

# --- Provider Functions ---

def send_message(bot: UserInfo, message: Message):
    params = {
        "channel": message.channel,
        "text": message.text,
        "attachments": message.attachments,
        "reply_broadcast":True
    }

    # Determine if the message is a reply to a parent message
    if message.parent_message_id:
        params["thread_ts"] = message.parent_message_id
    # If not a reply, but intended for a thread, set thread_ts to the thread ID
    elif message.thread_id:
        params["thread_ts"] = message.thread_id

    # Send the message using the Slack client
    bot.bot_client.chat_postMessage(**params)


def add_reaction(bot: UserInfo, reaction: ReactionEvent):
    # Translate Reaction to Slack's format
    if reaction.reaction in REACTION_DB:
        reaction.reaction = REACTION_DB[reaction.reaction]
    bot.bot_client.reactions_add(
        channel=reaction.channel_id,
        name=reaction.reaction,
        timestamp=reaction.message_id
    )


def remove_reaction(bot: UserInfo, reaction: ReactionEvent):
    # Translate Reaction to Slack's format
    if reaction.reaction in REACTION_DB:
        reaction.reaction = REACTION_DB[reaction.reaction]    
    bot.bot_client.reactions_remove(
        channel=reaction.channel_id,        
        name=reaction.reaction,
        timestamp=reaction.message_id
    )

def get_user_info(bot: UserInfo, user_id: str) -> UserInfo:
    user_info = UserProfile.lookup_userinfo(user_id)
    if user_info:
        return user_info

    user_info = UserInfo()
    response = bot.bot_client.users_info(user=user_id)
    if not response["ok"]:
        logging.error(f"Error getting user info for {user_id}: {response['error']}")
        return None
    uinfo = response["user"]

    user_info.id = uinfo["id"]
    user_info.platform = "slack"
    user_info.mention_tag = f"<@{user_info.id}>"
    user_info.username = uinfo['name']
    user_info.real_name = uinfo['real_name']
    user_info.title = uinfo['profile']['title']
    user_info.team = uinfo['team_id']
    user_info.is_bot = uinfo['is_bot']
    user_info.status = uinfo['profile']['status_text']
    UserProfile.add_userinfo_to_cache(user_info)
    return user_info


def _create_message_event_from_slack_message(bot: UserInfo, channel_id: str, message_content: dict) -> MessageEvent:
    message_info = MessageEvent()
    message_info.text = message_content.get("text", "")   
    message_info.direct_mention_bot = bot.mention_tag in message_info.text
    message_info.is_direct_message_channel = message_content.get("channel_type", None) == 'im'
    message_info.user_id = message_content.get("user", None)
    message_info.message_id = message_content.get("ts", None)
    message_info.channel_id = message_content.get("channel", channel_id)
    message_info.thread_id = message_content.get("thread_ts", None)


    # Handle Embedded Files
    if "files" in message_content:
        for file in message_content["files"]:
            file_info = EmbeddedFile()
            file_info.name = file["name"]
            file_info.url = file["url_private_download"]
            file_info.file_type = file["mimetype"]
            message_info.files.append(file_info)

    # Handle Embedded Links
    if "blocks" in message_content:
        for block in message_content["blocks"]:
            if block["type"] == "rich_text":
                for element in block["elements"]:
                    if element["type"] == "rich_text_section":
                        for link in element["elements"]:
                            if link["type"] == "link":
                                link_info = EmbeddedLink()
                                link_info.url = link["url"]
                                message_info.links.append(link_info)
  
    # Handler Reactions
    if "reactions" in message_content:
        for reaction in message_content["reactions"]:
            reaction_info = ReactionEvent()
            reaction_info.reaction = reaction["name"]
            reaction_info.user_id = reaction["users"]
            reaction_info.message_id = message_content["ts"]
            reaction_info.channel_id = message_content.get("channel",channel_id)
            message_info.reactions.append(reaction_info)
    
    return message_info

def get_message_info(bot: UserInfo, channel_id: str, message_id: str) -> Message:
    message_info = MessageEvent()
    response = bot.bot_client.conversations_history(channel=channel_id, latest=message_id, inclusive=True, include_all_metadata=True, limit=1)
    if not response["ok"]:
        logging.error(f"Error getting message info for {message_id}: {response['error']}")
        return None
    if not 'messages' in response:
        logging.error(f"No messages found for {message_id}")
        return None

    message_content = response["messages"][0]
    message_info = _create_message_event_from_slack_message(bot, channel_id, message_content)    
    return message_info


def get_messages_from_channel(bot: UserInfo, channel_id: str) -> list[MessageEvent]:
    response = bot.bot_client.conversations_history(channel=channel_id, include_all_metadata=True, limit=1000)
    if not response["ok"]:
        logging.error(f"Error getting messages from channel {channel_id}: {response['error']}")
        return None
    if not 'messages' in response:
        logging.error(f"No messages found for channel {channel_id}")
        return None
    messages = []
    for message_content in response["messages"]:
        message_info = _create_message_event_from_slack_message(bot, channel_id, message_content)
        messages.append(message_info)

    # Reverse the order of the messages because they're returned in reverse chronological order
    messages.reverse()
    return messages

def get_messages_from_thread(bot: UserInfo, channel_id: str, thread_id: str) -> list[MessageEvent]:
    response = bot.bot_client.conversations_replies(channel=channel_id, ts=thread_id, inclusive= True, include_all_metadata=True, limit=1000)
    if not response["ok"]:
        logging.error(f"Error getting messages from thread {thread_id}: {response['error']}")
        return None
    if not 'messages' in response:
        logging.error(f"No messages found for thread {thread_id}")
        return None
    messages = []
    for message_content in response["messages"]:
        message_info = _create_message_event_from_slack_message(bot, channel_id, message_content)
        messages.append(message_info)

    # Reverse the order of the messages because they're returned in reverse chronological order
    return messages

def get_thread_participants(bot:UserInfo, channel_id:str, thread_id:str) -> list[str]:
    try:
        # Fetch all messages from the thread
        result = bot.bot_client.conversations_replies(channel=channel_id, ts=thread_id)
        if not result['ok']:
            logging.error(f"Error fetching thread messages: {result['error']}")
            return []

        # Extract unique user IDs from the messages
        user_ids = set(message.get('user') for message in result['messages'])
        return list(user_ids)

    except Exception as e:
        logging.error(f"Error in get_thread_participants: {str(e)}")
        return []


async def get_previous_messages(bot, channel_id, message_ts=None, thread_ts=None):
    try:
        result = bot.bot_client.conversations_replies(channel=channel_id, ts=thread_ts)
        if not result['ok']:
            logging.error(f"Error fetching thread messages: {result['error']}")
            return []

        messages = []
        # Collect messages before the given message_ts
        for msg in result['messages']:
            message_event = _create_message_event_from_slack_message(bot,channel_id, msg)
            messages.append(message_event)

        return messages

    except Exception as e:
        logging.error(f"Error in get_previous_messages_slack: {str(e)}")
        return []



slack_bot_function_handler = ProviderFunctionsBase()
slack_bot_function_handler.send_message = send_message
slack_bot_function_handler.add_reaction = add_reaction
slack_bot_function_handler.remove_reaction = remove_reaction
slack_bot_function_handler.get_user_info = get_user_info
slack_bot_function_handler.get_message_info = get_message_info
slack_bot_function_handler.get_messages_from_channel = get_messages_from_channel
slack_bot_function_handler.get_messages_from_thread = get_messages_from_thread
slack_bot_function_handler.get_thread_participants = get_thread_participants
slack_bot_function_handler.get_previous_messages = get_previous_messages

# -- Internal Helpers --
def _get_bot_info(context):
    global slack_bot_function_handler
    bot_info = UserInfo()
    bot_info.id = context.bot_user_id
    bot_info.platform = "slack"
    bot_info.mention_tag = f"<@{context.bot_user_id}>"
    bot_info.username = "Slack Bot"
    bot_info.real_name = "Slackery Bottonson"
    bot_info.title = "Slack Bot"
    bot_info.is_bot = True
    bot_info.bot_client = app.client
    bot_info.bot_functions = slack_bot_function_handler
    return bot_info


# -- Event Handlers --

@app.event("message")
def handle_message_events(event, say, context):
    # Ignore deleted and changed messages
    if event.get('subtype', None) == 'message_deleted' or event.get('subtype', None) == 'message_changed':
        return
    # Don't process our own messages        
    if event['user'] == context.bot_id:
        return    

    bot_info = _get_bot_info(context)

    event_info = _create_message_event_from_slack_message(bot_info, event.get("channel",None), event)

    # Schedule the async event_handler to run asynchronously
    asyncio.run_coroutine_threadsafe(event_handler(bot_info, "message", event_info), new_loop)

@app.event("reaction_added")
def handle_reaction_added_events(event, say, context):
    bot_info = _get_bot_info(context)    
    reaction_info = ReactionEvent()
    reaction_info.reaction = event["reaction"]
    reaction_info.user_id = event["user"]
    reaction_info.message_id = event["item"]["ts"]
    asyncio.run_coroutine_threadsafe(event_handler(bot_info, "reaction_added", reaction_info), new_loop)


# This is meant to be replaced by whatever handler you need.
def event_handler(bot_info, event_type, event_data):
    raise NotImplementedError




# --- Public Function Class ---
def create_bot(custom_event_handler=None): 
    if(custom_event_handler):
        global event_handler
        event_handler = custom_event_handler



    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()

