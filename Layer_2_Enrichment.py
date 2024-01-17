import os
import json
import logging
from BotData import UserInfo, MessageEvent, ReactionEvent, Message
logging.basicConfig(level=logging.DEBUG)
import LocalData
import base64
import LLMFoundation
from VectorLexicon import VectorLexicon

IMG_DESC_CACHE_PATH = os.path.join(LocalData.CACHE_PATH, "img_desc_cache.json")


def load_img_desc_cache():
    if os.path.exists(IMG_DESC_CACHE_PATH):
        with open(IMG_DESC_CACHE_PATH, "r") as f:
            return json.load(f)
    else:
        return {}

def save_img_desc_cache(cache):
    with open(IMG_DESC_CACHE_PATH, "w") as f:
        json.dump(cache, f)

# This holds the image description cache of image urls that have been processed by a vision AI
IMAGE_DESC_CACHE = load_img_desc_cache()

async def process_images_for_vision(bot_info, file):
    """Asynchronously process image files in the message and prepare data for LLaVA."""

    # Check the URL against the image description cache
    if file.url in IMAGE_DESC_CACHE:
        # If the URL is in the cache, use the cached description
        return IMAGE_DESC_CACHE[file.url]['description']
    
    else:
        # Asynchronously encode the image to base64
        encoded_image = base64.b64encode(file.file_data).decode('utf-8')

        #file.description = await describe_image_gpt4v(encoded_image)
        summary = await LLMFoundation.describe_image_llava(encoded_image)         


        # Add the image description to the cache
        IMAGE_DESC_CACHE[file.url] = summary
        # Save the cache
        save_img_desc_cache(IMAGE_DESC_CACHE)
        return summary


async def create_message_transcript(previous_messages:list[MessageEvent]) -> str:
    transcript = "Below is the transcript of the conversation leading up to this message. If relevant, use this to help understand the context of the current request:\n\n ```\n"
    for previous_message in previous_messages:
        transcript += f"{previous_message.user_id}: {previous_message.text}\n"
        if previous_message.files:
            for file in previous_message.files:
                if 'image' in file.file_type:
                    transcript += f"*** Image Attached containing text: {file.ocr_text} and described as: {file.summary} ***\n"
                elif file.file_type == "pdf" or file.file_type == "txt":
                    transcript += f"*** Document Attached summarized as: {file.summary} ***\n"
      
        reactions = previous_message.reactions
        if len(reactions) > 0:
            for reaction in reactions:
                transcript += f"*User ID {reaction.user_id} reacted to this message with: {reaction.reaction}*\n"
            
    transcript += "\n```\n\n"
    return transcript

async def get_summary_of_text_files(bot_info, file):
    """Asynchronously process text files in the message and prepare data for inferece."""
    return await LLMFoundation.text_ask_local_llm(f"Summarize the Following Document: \n\n {file.file_data}")


async def process_layer(bot_info: UserInfo, message_event: MessageEvent, event_context):
    logging.info("----AI Phase 2: Enrichment----")
    new_reaction = ReactionEvent(reaction="phase_enrichment",message_id=message_event.message_id,channel_id=message_event.channel_id,user_id=bot_info.id,message_owner_id=message_event.user_id)
    await bot_info.bot_functions.call_add_reaction(bot_info, new_reaction)

    # Image Enrichment
    for file in message_event.files:
        if 'image' in file.file_type:
            file.summary = await process_images_for_vision(bot_info, file)
        elif "pdf" in file.file_type or "txt" in file.file_type:
            file.summary = await get_summary_of_text_files(bot_info, file)

    for message in event_context['previous_messages']:
        for file in message.files:
            if 'image' in file.file_type:
                file.summary = await process_images_for_vision(bot_info, file)
            elif "pdf" in file.file_type or "txt" in file.file_type:
                file.summary = await get_summary_of_text_files(bot_info, file)

    # Invote Lexicon Enrichment
    # TODO: Add Cached Lexicon
    vectordb = VectorLexicon()
    try:
        event_context['lexicon_enrichment'] = vectordb.enrich_prompt(message_event.text, user_clarification=False)
    except Exception as e:
        logging.error(f"Error enriching prompt: {e}")
        event_context['lexicon_enrichment'] = []

    if event_context['previous_messages']:
        event_context['conversation_transcript'] = create_message_transcript(event_context['previous_messages'])
    

    # Sentiment Analysis
    thought_prompt = f"Analyze the request: '{message_event.text}'. Reflect on the general intent and implications of this query. Do not answer the question; instead, focus on understanding and interpreting the request. After your analysis, prepare a response in a JSON format, where 'thought' captures your internal analysis process and 'explanation' is a restatement or clarification of the request as you understand it."
    event_context['sentiment_analysis'] = "Nevermind this" #await LLMFoundation.text_ask_local_llm(thought_prompt, temperature=0.5)

    await bot_info.bot_functions.call_remove_reaction(bot_info, new_reaction)
    return event_context