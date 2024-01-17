![alt text](https://github.com/batteryshark/NeuroNexus/blob/main/asset/icon.png)
# NeuroNexus - A ChatBotFramework for LLM Black Magic

This is a quick framework I've scaffolded together to support a Slack and/or Discord chatbot in a unified manner to support llm/genai pipelines. It allows users to structure rudimentary chatbots and leverage features of their chat clients to engage in rich interaction.

## Features

- Support for both Discord and Slack backends with an abstraction layer.
- Async by default
- Supports reactions and messages 
- Supports conversation chains and enabling historical context to LLMs
- Supports notes about conversation participants, allowing the llm to tailor output to the individuals/teams role.
- Supports LLM backends such as OpenAI/langchain/Ollama/etc.
- Supports Vision models (e.g. llava and gpt4vision) with built-in cache

## How to Set up a Bot

### Discord

1. Set up an application on https://discord.com/developers/
2. Under bot, make sure that presence intent, server members intent, and message content intent
3. Under OAuth2 URL generator, check 'bot' under scopes and set the permissions -  basically all text permissions except message everyone, and for general, change nickname, read/view messages/channels.
4. Use the generated URL to add the bot to your servers. 
5. Save the discord bot token to your .env file.

### Slack

1. Copy the 'manifest.yml' in this repo to get all the bot settings needed to run. Ensure socket mode is enabled for your bot.
2. Save the Slack App and Bot tokens to your .env file 


### Bot Environment
1. Install python3 (some modern version)
2. pip install -r requirements.txt for any module requirements.
3. Ensure your .env file is in the correct path (e.g. ~/.aiienv)
4. use 'start_discord.py' or 'start_slack.py' to start that respective iteration of the bot.


## How to Interact

There are two Ways to Start a new Conversation with the Bot:

1. Direct @mention the bot.
2. Direct message the bot via its DM/IM channel.

The bot will reply to your message

To continue a conversation with the bot, simply reply to the bot's message, or, in Slack's case, reply to a thread involving the bot.



## TODO

- Reaction feedback support
- Interactive elements (e.g. block-kit, discord.ui) to enrich responses
- Manual specification of a separate conversation/thread id to give the bot additional grounding.