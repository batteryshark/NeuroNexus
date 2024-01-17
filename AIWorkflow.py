# This module represents the AI Workflow. It is responsible for determining how a message should be processed by the LLM Workflow.

import logging

from datetime import datetime

from BotData import UserInfo, MessageEvent, ReactionEvent, Message

logging.basicConfig(level=logging.DEBUG)
import Layer_1_Context_Gathering
import Layer_2_Enrichment
import Layer_3_Processing
import Layer_4_Validation












async def AI_Phase_5_Request_Complete(bot_info: UserInfo, message_event: MessageEvent):
    logging.info("----AI Phase 5: Request Complete----")
    new_reaction = ReactionEvent(reaction="phase_request_complete",message_id=message_event.message_id,channel_id=message_event.channel_id,user_id=bot_info.id,message_owner_id=message_event.user_id)
    await bot_info.bot_functions.call_add_reaction(bot_info, new_reaction)
    pass

async def AI_Phase_6_Request_Failed(bot_info: UserInfo, message_event: MessageEvent):
    logging.info("----AI Phase 6: Request Failed----")
    new_reaction = ReactionEvent(reaction="phase_request_failed",message_id=message_event.message_id,channel_id=message_event.channel_id,user_id=bot_info.id,message_owner_id=message_event.user_id)
    await bot_info.bot_functions.call_add_reaction(bot_info, new_reaction)



# This logic is called when a message is received by the bot and determines if the message should be processed by the LLM Workflow
async def process_message_event(bot_info: UserInfo, message_event: MessageEvent):
    message_event.should_respond = False
    message_event.continued_conversation = False
    # Check for direct mention or direct message
    if message_event.direct_mention_bot or message_event.is_direct_message_channel:
        logging.info("Message is a direct mention or direct message to the bot")
        message_event.should_respond = True

    # Discord: Check if the message is a reply to the bot
    if bot_info.platform == "discord" and message_event.is_reply_to_bot:
        logging.info("Message is a reply to the bot")
        message_event.should_respond = True
        message_event.continued_conversation = True

    # Slack: Check if the message is in a thread AND the bot has been involved in this thread before
    if bot_info.platform == "slack" and message_event.thread_id is not None:
        message_event.thread_participant_ids = await bot_info.bot_functions.call_get_thread_participants(bot_info, message_event.channel_id, message_event.thread_id)
        if bot_info.id in message_event.thread_participant_ids:
            logging.info("Bot has been involved in this thread before")         
            message_event.should_respond = True
            message_event.continued_conversation = True

    # If the bot should respond, process the request
    if message_event.should_respond:        
        logging.info("Bot Should Respond")
        # Collect event history and additional relevant context
        event_context = await Layer_1_Context_Gathering.process_layer(bot_info, message_event)
        # Enrich the event context with additional information such as terms or entities
        event_context = await Layer_2_Enrichment.process_layer(bot_info, message_event, event_context)
        # Process the event and context to determine a plan for the bot
        processing_result = await Layer_3_Processing.process_layer(bot_info, message_event, event_context)
        # Validate the processing result
        validation_result = await Layer_4_Validation.process_layer(bot_info, message_event, event_context, processing_result)
        # If the validation result is successful, continue to Phase 5. Otherwise, continue to Phase 6
        if validation_result:
            await AI_Phase_5_Request_Complete(bot_info, message_event)
        else:
            await AI_Phase_6_Request_Failed(bot_info, message_event)
        
