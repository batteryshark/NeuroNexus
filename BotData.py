from dataclasses import dataclass, field, asdict
from typing import Optional,  Any, List
import asyncio
import inspect


# Represents a user's information
@dataclass
class UserInfo:
    id: str = ""
    platform: str = ""  # The chat provider (e.g., "slack")
    mention_tag: str = ""
    username: str = ""
    real_name: str = ""
    title: str = ""
    team: Optional[str] = None
    status: str = ""
    is_bot: bool = False
    bot_client: Optional[Any] = None  # Can hold any client object
    bot_functions: Optional[Any] = None
    bio: str = ""
    notes: List[str] = field(default_factory=list)  # Initialized as an empty list
    audience: str = ""

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        # Ensure notes is a list if it's present, or default to an empty list
        data['notes'] = data.get('notes', [])
        return UserInfo(**data)
    
    def __str__(self):
        return (f"UserInfo:\nID: {self.id}\nMention Tag: {self.mention_tag}\n"
                f"Username: {self.username}\nReal Name: {self.real_name}\n"
                f"Title: {self.title}\nTeam: {self.team}\nStatus: {self.status}\n"
                f"Is Bot: {self.is_bot}\nBio: {self.bio}\n AI Notes: {self.notes} \n How to Respond: {self.audience}")

# Represents any embedded file in a message.
@dataclass
class EmbeddedFile:
    name: str = ""
    url: str = ""
    file_type: str = ""  # Renamed 'type' to 'file_type' to avoid conflicts with Python's 'type'
    notes: str = ""
    ocr_text: str = ""
    summary: str = ""
    file_data: Optional[Any] = None  # Can hold any file data

    def __str__(self):
        return f"EmbeddedFile:\nName: {self.name}\nURL: {self.url}\nType: {self.file_type}\n"

# Represents any embedded link in a message.
@dataclass
class EmbeddedLink:
    url: str = ""
    notes: str = ""
    def __str__(self):
        return f"EmbeddedLink:\nURL: {self.url}\nNotes: {self.notes}\n"

# Represents a reaction event received from or sent to a provider
@dataclass
class ReactionEvent:
    reaction: str = ""  # name of reaction (e.g., 'white_check_mark')
    user_id: Optional[str] = None  # user id of the entity responsible for the reaction
    message_id: Optional[str] = None  # The Message id that the reaction is attached to.
    message_owner_id: Optional[str] = None  # The user id of the message owner
    channel_id: Optional[str] = None  # The id of the channel the message is in
    notes: str = ""  # Notes for AI about the Reaction

    def __str__(self):
        return (f"ReactionEvent:\nReaction: {self.reaction}\nUser ID: {self.user_id}\n"
                f"Message ID: {self.message_id}\nNotes: {self.notes}")

# Represents a message received from a provider
@dataclass
class MessageEvent:
    text: str = ""  # The message text
    user_id: Optional[str] = None  # user id of the entity responsible for the message
    message_id: Optional[str] = None  # The id of the message
    channel_id: Optional[str] = None  # The id of the channel the message is in
    is_reply_to_bot: bool = False  # True if this message is a reply to a bot's message
    direct_mention_bot: bool = False # True if this message directly mentions the bot.
    is_direct_message_channel: bool = False  # True if the message is in a direct message channel
    thread_participant_ids: Optional[List[str]] = None
    continued_conversation: bool = False
    should_respond: bool = False # True if the bot should respond to this message
    files: List[EmbeddedFile] = field(default_factory=list)  # List of EmbeddedFile objects
    links: List[EmbeddedLink] = field(default_factory=list)  # List of EmbeddedLink objects
    reactions: List[ReactionEvent] = field(default_factory=list)  # List of ReactionEvent objects
    thread_id: Optional[str] = None  # The id of the thread the message is in
    parent_message_id: Optional[str] = None  # The id of the parent message if this message is a reply
    notes: Optional[str] = ""  # Notes for AI about the message

    def __str__(self):
        files_str = "\nFiles:\n" + "\n".join([str(file) for file in self.files]) if self.files else ""
        links_str = "\nLinks:\n" + "\n".join([str(link) for link in self.links]) if self.links else ""
        notes_str = f"Notes: {self.notes}\n" if self.notes else ""
        return (f"[MessageEvent] User ID: {self.user_id} Message ID: {self.message_id} Thread ID: {self.thread_id}\n"
                f"Message: {self.text}\n{notes_str}{files_str}{links_str}\n")

# Represents a message to be sent to a provider
@dataclass
class Message:
    text: Optional[str]
    platform: Optional[str]  # 'discord' or 'slack'
    parent_message_id: Optional[str] = None  # ID of the message to reply to, if any
    channel: Optional[str] = None  # Channel ID for Slack or Discord
    thread_id: Optional[str] = None  # Thread ID if the message is for a thread
    attachments: List[str] = field(default_factory=list)  # List of attachment URLs or IDs

    def __str__(self):
        attachments_str = ', '.join(self.attachments) if self.attachments else 'None'
        return (f"Message:\nText: {self.text}\nParent Message ID: {self.parent_message_id}\n"
                f"Channel: {self.channel}\nThread ID: {self.thread_id}\n"
                f"Attachments: {attachments_str}\nPlatform: {self.platform}")


# Method Adapter for Various Providers
class ProviderFunctionsBase:
    def __init__(self):
        self.send_message = None
        self.add_reaction = None
        self.remove_reaction = None
        self.get_user_info = None
        self.get_messages_from_channel = None
        self.get_messages_from_thread = None
        self.get_message_info = None
        self.get_thread_participants = None
        self.get_previous_messages = None

    async def async_adapter(self, method, *args, **kwargs):
        if inspect.iscoroutinefunction(method):
            return await method(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, method, *args, **kwargs)

    async def call_send_message(self, bot, message):
        await self.async_adapter(self.send_message, bot, message)

    async def call_add_reaction(self, bot, reaction):
        await self.async_adapter(self.add_reaction, bot, reaction)

    async def call_remove_reaction(self, bot, reaction):
        await self.async_adapter(self.remove_reaction, bot, reaction)

    async def call_get_user_info(self, bot, user_id):
        return await self.async_adapter(self.get_user_info, bot, user_id)

    async def call_get_messages_from_channel(self, bot, channel_id):
        return await self.async_adapter(self.get_messages_from_channel, bot, channel_id)

    async def call_get_messages_from_thread(self, bot, channel_id, thread_id):
        return await self.async_adapter(self.get_messages_from_thread, bot, channel_id, thread_id)

    async def call_get_message_info(self, bot, channel_id, message_id):
        return await self.async_adapter(self.get_message_info, bot, channel_id, message_id)
    
    async def call_get_thread_participants(self, bot, channel_id, thread_id):
        return await self.async_adapter(self.get_thread_participants, bot, channel_id, thread_id)
    
    async def call_get_previous_messages(self, bot, channel_id, message_id, thread_id):
        return await self.async_adapter(self.get_previous_messages, bot, channel_id, message_id, thread_id)