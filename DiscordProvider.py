import os

import discord
import asyncio
import emoji

from BotData import UserInfo, ReactionEvent, MessageEvent, EmbeddedFile, EmbeddedLink, Message, ProviderFunctionsBase
import logging
import UserProfile
import asyncio

REACTION_DB = {
    'phase_context_gathering': emoji.emojize(':eyes:',language='alias'),
    'phase_enrichment': emoji.emojize(':frame_with_picture:',language='alias'),
    'phase_processing': emoji.emojize(':brain:',language='alias'),
    'phase_validation': emoji.emojize(':mag:',language='alias'),
    'phase_request_complete': emoji.emojize(':white_check_mark:',language='alias'),
    'phase_request_failed': emoji.emojize(':x:',language='alias'),
    'looking': emoji.emojize(':eyes:',language='alias'),
    'thinking':emoji.emojize(':brain:',language='alias'),
    'thumbs_up':emoji.emojize(':thumbsup:',language='alias'),
    'thumbs_down':emoji.emojize(':thumbsdown:',language='alias'),
    'green_check':emoji.emojize(':white_check_mark:',language='alias'),
    'red_x':emoji.emojize(':x:',language='alias'),
    'process_image':emoji.emojize(':frame_with_picture:',language='alias'),
}

def convert_reaction(reaction_text):
    reaction_emoji = REACTION_DB.get(reaction_text,None)
    if reaction_emoji is not None:
        return reaction_emoji
        
    return emoji.emojize(reaction_text)    

async def convert_discord_message_to_message_event(bot_info, message):
    message_info = MessageEvent()
    message_info.text = message.content
    message_info.user_id = message.author.id
    message_info.message_id = message.id
    message_info.channel_id = message.channel.id

    message_info.is_direct_message_channel = isinstance(message.channel, discord.DMChannel)
    message_info.direct_mention_bot = bot_info.mention_tag in message.content

    # Set parent_message_id if the message is a reply
    if message.reference and isinstance(message.reference.resolved, discord.Message):
        message_info.parent_message_id = message.reference.message_id

    # Check if the message is a reply to another message
    if message.reference and isinstance(message.reference.resolved, discord.Message):
        # Set parent_message_id if the message is a reply
        message_info.parent_message_id = message.reference.message_id
        # Check if the referenced message is by the bot
        message_info.is_reply_to_bot = message.reference.resolved.author.id == bot_info.id


    # Check if the message is a reply in a thread
    if message.reference and isinstance(message.reference.resolved, discord.Message):
        message_info.thread_id = message.reference.resolved.channel.id
    else:
        message_info.thread_id = None

    message_info.files = [EmbeddedFile(name=attachment.filename, url=attachment.url, file_type=attachment.content_type) for attachment in message.attachments]
    message_info.links = [EmbeddedLink(url=embed.url) for embed in message.embeds]

    message_info.reactions = []
    for reaction in message.reactions:
        users = [user async for user in reaction.users()]
        for user in users:
            reaction_event = ReactionEvent(
                reaction=REACTION_DB.get(reaction.emoji, None),
                user_id=user.id,
                message_id=message.id
            )
            message_info.reactions.append(reaction_event)

    return message_info




# --- Provider Functions ---

def get_user_info(bot: UserInfo, user_id: str) -> UserInfo:
    user_info = UserProfile.lookup_userinfo(user_id)
    if user_info:
        return user_info    
    
    user_info = UserInfo()
    user = bot.bot_client.get_user(user_id)
    if user == None:
        logging.error(f"Could not find user with ID {user_id}")
        return None
    user_info.id = user_id
    user_info.platform = "discord"
    user_info.mention_tag = f"<@{user_id}>"
    user_info.username = user.name
    user_info.real_name = user.global_name
    user_info.title = "Discord User"
    user_info.is_bot = user.bot
    UserProfile.add_user_info_to_cache(user_info)
    return user_info

async def send_message(bot: UserInfo, message: Message):
    channel = bot.bot_client.get_channel(message.channel)
    if channel is None:
        logging.error(f"Could not find channel with ID {message.channel}")
        return

    # Function to send a message chunk
    async def send_chunk(chunk, parent_message=None):
        await channel.send(chunk, reference=parent_message)

    # If message is a reply, fetch the parent message
    parent_message = None
    if message.parent_message_id:
        parent_message = await channel.fetch_message(message.parent_message_id)

    # Split message into chunks of 2000 characters if necessary
    chunk_size = 2000
    if len(message.text) > chunk_size:
        chunks = [message.text[i:i+chunk_size] for i in range(0, len(message.text), chunk_size)]
    else:
        chunks = [message.text]

    # Send each chunk
    for chunk in chunks:
        await send_chunk(chunk, parent_message)


async def add_reaction(bot: UserInfo, reaction: ReactionEvent) -> None:
    try:
        # Attempt to get the channel (works for both guild and DM channels)
        channel = bot.bot_client.get_channel(reaction.channel_id)

        # If the channel is not found, it might be a DM, so fetch the user and get/create DM channel
        if channel is None:
            user = await bot.bot_client.fetch_user(reaction.message_owner_id)
            channel = await user.create_dm()

        # If still no channel, log an error
        if channel is None:
            logging.error(f"Unable to find or create channel for user {reaction.message_owner_id}")
            return

        # Fetch the message from the channel and add the reaction
        message = await channel.fetch_message(reaction.message_id)
        await message.add_reaction(convert_reaction(reaction.reaction))

    except Exception as e:
        logging.error(f"Error in add_reaction {reaction.reaction}: {str(e)}")



async def remove_reaction(bot: UserInfo, reaction: ReactionEvent) -> None:
    # Attempt to get the channel normally
    channel = bot.bot_client.get_channel(reaction.channel_id)

    # Fetch the message and add the reaction
    try:
        message = await channel.fetch_message(reaction.message_id)
        await message.remove_reaction(convert_reaction(reaction.reaction), member=bot.bot_client.user)
    except Exception as e:
        logging.error(f"Error adding reaction: {e}")   


async def get_messages_from_channel(bot: UserInfo, channel_id: str) -> list:
    channel = bot.bot_client.get_channel(channel_id)
    messages = []
    async for message in channel.history(limit=100):
        message_event = await convert_discord_message_to_message_event(bot,message)
        messages.append(message_event)
    messages.reverse()
    return messages


async def get_messages_from_thread(bot: UserInfo, channel_id: str, thread_id: str) -> list:
    # First, get the thread channel
    thread_channel = bot.bot_client.get_channel(thread_id)

    # Check if the channel is actually a thread
    if not isinstance(thread_channel, discord.Thread):
        logging.error(f"The channel with ID {thread_id} is not a thread.")
        return []

    # Now fetch messages from the thread channel
    messages = []
    async for message in thread_channel.history(limit=100):
        message_event = await convert_discord_message_to_message_event(bot,message)
        messages.append(message_event)
    messages.reverse()
    return messages

async def get_message_info(bot: UserInfo, channel_id: str, message_id: str) -> Message:
    channel = bot.bot_client.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    message_info = await convert_discord_message_to_message_event(bot,message)
    return message_info


async def get_previous_messages(bot: UserInfo,  channel_id: str, message_id: str, thread_id: str) -> list[MessageEvent]:
    channel = bot.bot_client.get_channel(channel_id)
    if not channel:
        logging.error(f"Channel not found: {channel_id}")
        return []

    messages = []
    async def fetch_replies(msg_id):
        msg = await channel.fetch_message(msg_id)
        if msg.reference and msg.reference.message_id:
            messages.append(await convert_discord_message_to_message_event(bot,msg))
            await fetch_replies(msg.reference.message_id)

    await fetch_replies(message_id)

    return messages

discord_bot_function_handler = ProviderFunctionsBase()

discord_bot_function_handler.send_message = send_message
discord_bot_function_handler.add_reaction = add_reaction
discord_bot_function_handler.remove_reaction = remove_reaction
discord_bot_function_handler.get_user_info = get_user_info
discord_bot_function_handler.get_message_info = get_message_info
discord_bot_function_handler.get_messages_from_channel = get_messages_from_channel
discord_bot_function_handler.get_messages_from_thread = get_messages_from_thread
discord_bot_function_handler.get_previous_messages = get_previous_messages

# -- Internal Helpers --
def _get_bot_info(client):
    global discord_bot_function_handler
    bot_info = UserInfo()
    bot_info.id = client.user.id
    bot_info.platform = "discord"
    bot_info.mention_tag = f"<@{client.user.id}>"
    bot_info.username = client.user.name
    bot_info.real_name = client.user.global_name
    bot_info.title = "Discord Bot"
    bot_info.is_bot = True
    bot_info.bot_client = client
    bot_info.bot_functions = discord_bot_function_handler
    return bot_info


class DiscordHandler(discord.Client):

    async def on_message(self, message):
        # Don't respond to ourselves
        if message.author == self.user:
            return
        
        bot_info = _get_bot_info(self)    
        message_info = await convert_discord_message_to_message_event(bot_info, message)
        asyncio.create_task(event_handler(bot_info, "message", message_info))

    # Note: We have to use 'raw' events to get reactions from messages not in our current running cache.
    async def on_raw_reaction_add(self, payload):   
        if payload.user_id == self.user.id:
            return
        
        bot_info = _get_bot_info(self)    
        reaction_info = ReactionEvent()
        reaction_info.reaction = str(payload.emoji.name)
        reaction_info.user_id = payload.user_id
        reaction_info.message_id = payload.message_id
        asyncio.create_task(event_handler(bot_info, "reaction_added", reaction_info))


# This is meant to be replaced by whatever handler you need.
def event_handler(bot_info, event_type, event_data):
    raise NotImplementedError

# --- Public Function Class ---
def create_bot(custom_event_handler=None): 
    if(custom_event_handler):
        global event_handler
        event_handler = custom_event_handler


    bot_key = os.environ.get("DISCORD_BOT_KEY","")
    if bot_key == "":
        logging.error("[ERROR] No Discord Bot Key Provided")
        return False,None
    intents = discord.Intents.default()
    
    intents.members = True
    intents.messages = True
    intents.reactions = True
    intents.message_content = True
    intents.guilds = True

    client = DiscordHandler(intents=intents)
    client.run(bot_key)
