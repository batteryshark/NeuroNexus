# Management of Local Data and Caches
import os
import json
from dotenv import load_dotenv
from BotData import UserInfo

BASE_PATH = os.path.expanduser("~/.chatbot/")
if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

CACHE_PATH = os.path.join(BASE_PATH, "cache")
if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

# Make .env if it doesnt exist
ENV_PATH = os.path.join(BASE_PATH, ".env")
if not os.path.exists(ENV_PATH):
    with open(ENV_PATH, "w") as f:
        f.write("")

def load_local_data():
    load_dotenv(ENV_PATH)

