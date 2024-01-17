# This layer controls the actual processing plan. It is responsible for determining the plan for the bot to respond to the user's request by engaging variopus workflows and agents to complete the request.
import logging

from BotData import UserInfo, MessageEvent, ReactionEvent, Message

import LLMFoundation

logging.basicConfig(level=logging.INFO)




async def process_layer(bot_info: UserInfo, message_event: MessageEvent, event_context):
    processing_result = None
    logging.info("----AI Phase 3: Processing----")
    new_reaction = ReactionEvent(reaction="phase_processing",message_id=message_event.message_id,channel_id=message_event.channel_id,user_id=bot_info.id,message_owner_id=message_event.user_id)
    await bot_info.bot_functions.call_add_reaction(bot_info, new_reaction)
    # TODO ADD CODE
    #TODO Future - Break Down Problem into Sub-Problems and give to Dispatch AI to determine COA
    # For now, we will enrich the prompt and use the default llm.
    prompt = "Current Date: " + event_context['current_date'] + "\n"    

    prompt += f"You are a helpful AI Assistant named {bot_info.id}.  You are in a conversation with {message_event.user_id} and will answer their request to the best of your ability.\n"

    # Only include user info to prompt if we have notes, audience, or bio
    if event_context['author_info'].notes or event_context['author_info'].audience or event_context['author_info'].bio:
        prompt += f"``` Use their User Info to influence your responses \n User Info: \n{event_context['author_info']}\n```"

    # Include Conversation history if needed
    if event_context['previous_messages']:
        prompt += event_context['conversation_transcript']

    # Include Thread Participants if needed
    if event_context['thread_participants']:
        prompt += "``` Use the following Thread Participants to influence your responses: \n"
        for participant in event_context['thread_participants']:
            prompt += f"{participant}\n"
        prompt += "```"

    # Include Mentioned Participants if needed
    if event_context['mentioned_participants']:
        prompt += "``` Use the following Mentioned Participants to influence your responses: \n"
        for participant_id in event_context['mentioned_participants']:
            prompt += f"\n\n{event_context['mentioned_participants'][participant_id]}\n\n"
        prompt += "```"

    # Include Lexicon Enrichment if needed
    """
    if event_context['lexicon_enrichment']:
        prompt += "``` Use the following Lexicon Enrichment to influence your responses: \n"
        for enrichment in event_context['lexicon_enrichment']:
            prompt += f"{enrichment}\n"
        prompt += "```"
    """

    # Include any file Summaries
    if message_event.files:
        for file in message_event.files:
            if 'image' in file.file_type:
                prompt += f"*** Image Attached containing text: {file.ocr_text} and described as: {file.summary} ***\n"
            elif file.file_type == "pdf" or file.file_type == "txt":
                prompt += f"*** Document Attached summarized as: {file.summary} ***\n"    

    # Remove the bot's name from the prompt
    message_event.text = message_event.text.replace(f"<@{bot_info.id}>", "").replace(f"<@!{bot_info.id}>", "")
    # Finally, Include the Actual Request
    prompt += f"``` Request: \n{message_event.text}\n```"

    logging.info("----------------------")
    logging.info("Prompt: " + prompt)
    logging.info("----------------------")

    # Send the Prompt to the LLM
    response = await LLMFoundation.text_ask_local_llm(prompt)
    processing_result = {'result':'OK', 'response':response}

    await bot_info.bot_functions.call_remove_reaction(bot_info, new_reaction)
    return processing_result
