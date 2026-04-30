import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

config = {
    "app_id": os.getenv("APP_ID", ""),
    "app_secret": os.getenv("APP_SECRET", ""),
    "page_id": os.getenv("PAGE_ID", ""),
    "page_access_token": os.getenv("PAGE_ACCESS_TOKEN", "")
}

with open("config.json", "w") as f:
    json.dump(config, f, indent=2)

print("config.json generated from .env variables.")
