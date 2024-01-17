# Logic surrounding the initial phase of the AI workflow. This phase is responsible for gathering context about the event that triggered the AI workflow.
import PyPDF2
import aiohttp
import pytesseract
from BotData import UserInfo, MessageEvent, ReactionEvent
from PIL import Image
import re
import io
import logging
from datetime import datetime
import os

async def get_pdf_text(url_path, platform='discord'):
    async with aiohttp.ClientSession() as session:
        if platform == 'slack':
            async with session.get(url_path, headers={"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"}) as response:
                f = await response.read()
                pdfReader = PyPDF2.PdfFileReader(f)
                # Get All Pages of Text and return
                text = ""
                for page in pdfReader.pages:
                    text += page.extractText()
                return text
        else:
            async with session.get(url_path) as response:
                f = await response.read()
                pdfReader = PyPDF2.PdfFileReader(f)
                # Get All Pages of Text and return
                text = ""
                for page in pdfReader.pages:
                    text += page.extractText()
                return text
                        

async def get_txt_text(url_path, platform='discord'):
    async with aiohttp.ClientSession() as session:
        if platform == 'slack':
            async with session.get(url_path, headers={"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"}) as response:
                response.raise_for_status()
                data = await response.read()
                return data.decode('utf-8')  
        else:
            async with session.get(url_path) as response:
                response.raise_for_status()
                data = await response.read()
                return data.decode('utf-8')  
        
async def get_image_data(url_path, platform='discord'):
    async with aiohttp.ClientSession() as session:
        if platform == 'slack':
            async with session.get(url_path, headers={"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"}) as response:
                response.raise_for_status()
                return await response.read()
        else:
            async with session.get(url_path) as response:
                response.raise_for_status()
                return await response.read()            
            



async def analyze_mentions(bot_info: UserInfo, author_id, message_event: MessageEvent, mentioned_participants):
    mention_regex = r"<@(\w+)>"
    if re.search(mention_regex, message_event.text):
        for mention in re.findall(mention_regex, message_event.text):
            if mention != str(bot_info.id) and mention != str(author_id) and mention not in mentioned_participants:              
                mention_user_info = await bot_info.bot_functions.call_get_user_info(bot_info, mention)
                if mention_user_info is not None:
                    mentioned_participants[mention] = mention_user_info
                    
    return mentioned_participants




async def process_layer(bot_info: UserInfo, message_event: MessageEvent):
    logging.info("----AI Phase 1: Context Gathering----")
    new_reaction = ReactionEvent(reaction="phase_context_gathering",message_id=message_event.message_id,channel_id=message_event.channel_id,user_id=bot_info.id,message_owner_id=message_event.user_id)
    await bot_info.bot_functions.call_add_reaction(bot_info, new_reaction)

    event_context = {
        'previous_messages': [],
        'message_transcript': [],
        'author_info': None,
        'thread_participants': {},
        'mentioned_participants': {},
        'current_date': datetime.now().strftime("%m/%d/%Y")
    }

    # Get the info of the author of the message
    event_context['author_info'] = await bot_info.bot_functions.call_get_user_info(bot_info, message_event.user_id)

    # If the message was part of a continued conversation, we need to get the previous messages in the thread.
    # We also need to get the info of each user from those previous messages.
    if message_event.continued_conversation:
        event_context['previous_messages'] = await bot_info.bot_functions.call_get_previous_messages(bot_info, message_event.channel_id, message_event.message_id, message_event.thread_id)
        # If we have previous messages, we also need to get the info of each user from those previous messages.
        # We don't want the bot info or the user info of the message we are responding to.
        if len(message_event.thread_participant_ids):
            for tpid in message_event.thread_participant_ids:
                if tpid != bot_info.id and tpid != message_event.user_id:
                    event_context['thread_participants'][tpid] = await bot_info.bot_functions.call_get_user_info(bot_info, tpid)
    
    # If any message contains a mention, we need to get the info of each user mentioned.
    # Regex to find mentions: <@USERID>                              
    event_context['mentioned_participants'] = await analyze_mentions(bot_info, message_event.user_id, message_event, event_context['mentioned_participants'])

    for j in range(0, len(event_context['previous_messages'])):
        message = event_context['previous_messages'][j]
        for i in range(0, len(message.files)):
            if "pdf" in message.files[i].file_type:
                message.files[i].file_data = await get_pdf_text(message.files[i].url, bot_info.platform)
            elif "txt" in message.files[i].file_type:
                message.files[i].file_data = await get_txt_text(message.files[i].url, bot_info.platform)
            elif "image" in message.files[i].file_type:
                file_data = await get_image_data(message.files[i].url, bot_info.platform)
                # Get OCR Data for Images
                message.files[i].ocr_text = pytesseract.image_to_string(Image.open(file_data))
                message.files[i].file_data = file_data

    # Get File and Image Data for Current Message
    for file in message_event.files:
        if "pdf" in file.file_type:
            file.file_data = await get_pdf_text(file.url, bot_info.platform)
        elif "txt" in file.file_type:
            file.file_data = await get_txt_text(file.url, bot_info.platform)
        elif "image" in file.file_type:
            file_data = await get_image_data(file.url, bot_info.platform)
            # Get OCR Data for Images
            image = Image.open(io.BytesIO(file_data))
            file.ocr_text = pytesseract.image_to_string(image)
            file.file_data = file_data


    await bot_info.bot_functions.call_remove_reaction(bot_info, new_reaction)
    return event_context