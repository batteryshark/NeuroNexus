from dotenv import load_dotenv

import LocalData
load_dotenv(LocalData.ENV_PATH)

from ChatBot import run_slack

if __name__ == "__main__":
    run_slack()

