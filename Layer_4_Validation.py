import re
import logging
import json
import asyncio
from UserProfile import add_userinfo_to_cache
from BotData import UserInfo, MessageEvent, ReactionEvent, Message

import threading
import LLMFoundation

logging.basicConfig(level=logging.DEBUG)


# In case we need a parallel event loop for stuff
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

new_loop = asyncio.new_event_loop()
t = threading.Thread(target=start_loop, args=(new_loop,))
t.start()



async def fix_user_mentions(text, platform="slack"):
    """
    Fixes user mentions in the given text for Slack or Discord.

    Args:
    text (str): The text with potential user mentions.
    platform (str): The platform type ('slack' or 'discord').

    Returns:
    str: Text with user mentions fixed.
    """
    if platform == "slack":
        # Slack user IDs typically start with 'U'
        pattern = r"<@!?([U][A-Z0-9]+)>|@!?([U][A-Z0-9]+)|([U][A-Z0-9]+)"
    elif platform == "discord":
        # Discord user IDs are numeric and typically at least 15 digits long
        pattern = r"<@!?([0-9]{15,})>|@!?([0-9]{15,})|([0-9]{15,})"

    def format_mention(match):
        user_id = match.group(1) or match.group(2) or match.group(3)
        if platform == "slack":
            return f"<@{user_id}>"
        elif platform == "discord":
            return f"<@!{user_id}>"

    fixed_text = re.sub(pattern, format_mention, text)

    return fixed_text

async def update_notes_thread(user_info, message, response):
    notes_prompt = """
    Based on the user's profile, user's request, and assistant response, provide any new and relevant personal characteristics, interests, and facts relevant to the user's personality profile.\n
    Exclude notes about the conversation or interaction. If no update is necessary, respond with an empty JSON array '[]'.\n
    """
    notes_prompt += f"User Info: \n{user_info}\n"
    notes_prompt += f"Request: {message.user_id}: {message.text}\n"
    notes_prompt += f"Assistant Response: {response}\n"
    notes_prompt += f"Current Notes in JSON Format: {json.dumps(user_info.notes)}\n"
    notes_prompt += "New Notes (in JSON List Format): "


    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        notes_response = await LLMFoundation.text_ask_ai(notes_prompt, temperature=0.5)
        logging.info(f"Notes Response: {notes_response}")

        if notes_response != '[]':
            try:
                new_notes = json.loads(notes_response)
                # Process and break if valid response
                for note in new_notes:
                    if note not in user_info.notes:
                        user_info.notes.append(note)
                add_userinfo_to_cache(user_info)
                logging.info(f"Updated User Info: {user_info}")
                break
            except json.JSONDecodeError:
                logging.warning(f"Retry {retry_count + 1}: Failed to decode JSON from the LLM response.")

        retry_count += 1

    if retry_count == max_retries:
        logging.error("Max retries reached, failed to obtain valid JSON response.")


async def process_layer(bot_info: UserInfo, message_event: MessageEvent, event_context, processing_result):
    logging.info("----AI Phase 4: Validation----")
    new_reaction = ReactionEvent(reaction="phase_validation",message_id=message_event.message_id,channel_id=message_event.channel_id,user_id=bot_info.id,message_owner_id=message_event.user_id)
    await bot_info.bot_functions.call_add_reaction(bot_info, new_reaction)
    
    if processing_result['result'] != 'OK':
        logging.error("Processing Failed")
        await bot_info.bot_functions.call_remove_reaction(bot_info, new_reaction)
        return False
    
    response = processing_result['response']
    # Remove the bot's name from the response
    if response.startswith(f"{bot_info.id}:"):
        response = response[len(f"{bot_info.id}:"):].strip()

    # Fix user mentions in the response
    response = await fix_user_mentions(response, bot_info.platform)      
    
    # Update User Profile Notes if Necessary
    asyncio.run_coroutine_threadsafe(update_notes_thread(event_context['author_info'],message_event, response), new_loop)


    # Send the Final Response Message to our user.
    new_message = Message(text=response,platform=bot_info.platform)
    new_message.thread_id = message_event.thread_id
    new_message.parent_message_id = message_event.message_id
    new_message.channel = message_event.channel_id
    await bot_info.bot_functions.call_send_message(bot_info, message=new_message)

    await bot_info.bot_functions.call_remove_reaction(bot_info, new_reaction)
    # This will send the result and choose to either go to Phase 5 or Phase 6
    return True