# Management of the User Personality Profile
import os
import json
import LocalData
from BotData import UserInfo

USER_INFO_CACHE_PATH = os.path.join(LocalData.CACHE_PATH, "userinfo_cache.json")

def load_userinfo_cache():
    if os.path.exists(USER_INFO_CACHE_PATH):
        with open(USER_INFO_CACHE_PATH, "r") as f:
            data = json.load(f)
            return {str(user_id): UserInfo.from_dict(user_data) for user_id, user_data in data.items()}
    return {}

def save_userinfo_cache(cache):
    with open(USER_INFO_CACHE_PATH, "w") as f:
        # Ensure user IDs are converted to strings for consistency
        json.dump({str(user_id): user_info.to_dict() for user_id, user_info in cache.items()}, f, indent=4)

def add_userinfo_to_cache(userinfo):
    # Ensure userinfo.id is a string for consistency
    USERINFO_CACHE[str(userinfo.id)] = userinfo
    save_userinfo_cache(USERINFO_CACHE)

def lookup_userinfo(user_id):
    # Convert user_id to string for lookup to maintain consistency
    return USERINFO_CACHE.get(str(user_id), None)

USERINFO_CACHE = load_userinfo_cache()

