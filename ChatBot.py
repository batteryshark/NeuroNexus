import logging
import time
import traceback
from BotData import ReactionEvent, Message

import SlackProvider
import DiscordProvider

import AIWorkflow


logging.basicConfig(level=logging.DEBUG)



# -- Test Functions --
async def test_reaction(bot_info, message_event):
    new_reaction = ReactionEvent(reaction="thinking",message_id=message_event.message_id,channel_id=message_event.channel_id,message_owner_id=message_event.user_id)

    await bot_info.bot_functions.call_add_reaction(bot_info, new_reaction)

    time.sleep(5)

    await bot_info.bot_functions.call_remove_reaction(bot_info, new_reaction)
    new_reaction.reaction = "green_check"
    await bot_info.bot_functions.call_add_reaction(bot_info, new_reaction)
    time.sleep(1)
    await bot_info.bot_functions.call_remove_reaction(bot_info, new_reaction)

async def test_reply(bot_info, message_event, reply=True):
    new_message = Message(text="https://www.youtube.com/watch?v=zDtQgBBA-n0",platform=bot_info.platform)
    new_message.thread_id = message_event.thread_id
    if reply:
        new_message.parent_message_id = message_event.message_id

    new_message.channel = message_event.channel_id
    await bot_info.bot_functions.send_message(bot_info, message=new_message)

async def test_channel_history(bot_info, message_event):
    logging.info("Getting Channel History")
    channel_history = await bot_info.bot_functions.call_get_messages_from_channel(bot_info, message_event.channel_id)
    for message in channel_history:
        logging.info(message)

async def test_thread_history(bot_info, message_event):
    logging.info("Getting Thread History")
    thread_history = await bot_info.bot_functions.call_get_messages_from_thread(bot_info, message_event.channel_id, message_event.thread_id)
    for message in thread_history:
        logging.info(message)

async def test_get_sender_info(bot_info, message_event):
    logging.info("Getting Sender Info")
    sender_info = await bot_info.bot_functions.call_get_user_info(bot_info, message_event.user_id)
    logging.info(sender_info)

async def test_get_message_info(bot_info, message_event):
    logging.info("Getting Message Info")
    message_info = await bot_info.bot_functions.call_get_message_info(bot_info, message_event.channel_id,message_event.message_id)
    logging.info(message_info)

# -- End Test Functions --
    


        


# -- Startup Code --
async def event_handler(bot_info, event_type, event_data):
    if event_type == "message":
        try:
            await AIWorkflow.process_message_event(bot_info, event_data)
        except Exception as e:
            traceback_info = traceback.format_exc()            
            logging.error(f"Error processing message event: {e} {traceback_info}")
        
        #await test_reaction(bot_info, event_data)
        #await test_reply(bot_info, event_data, reply=True)
        #await test_channel_history(bot_info, event_data)
        #await test_get_sender_info(bot_info, event_data)
        #await test_get_message_info(bot_info, event_data)        
        #await test_thread_history(bot_info, event_data)

    elif event_type == "reaction_added":
        logging.info(f"Reaction: {event_data}")

    else:
        logging.warn("Received an unhandled " + event_type + " event")

def run_slack():
    global event_handler
    bot = SlackProvider.create_bot(event_handler)

def run_discord():
    global event_handler
    bot = DiscordProvider.create_bot(event_handler)




