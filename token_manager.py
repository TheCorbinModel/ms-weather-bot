import os
import json
import time
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("token_manager")

class TokenManager:
    """Manages Facebook Page Access Tokens with optional auto-refresh."""

    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        """Load credentials from environment variables if set, else from the JSON config file."""
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
        # Try to load from environment, fallback to config.json
        self.app_id = os.environ.get("APP_ID", self.config["app_id"])
        self.app_secret = os.environ.get("APP_SECRET", self.config["app_secret"])
        self.page_id = os.environ.get("PAGE_ID", self.config["page_id"])
        self.page_access_token = os.environ.get("PAGE_ACCESS_TOKEN", self.config["page_access_token"])
        # "system_user" or "long_lived"
        self.token_type = self.config.get("token_type", "long_lived")

    def save_config(self):
        """Persist updated config (e.g., after token refresh) to disk."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def refresh_long_lived_token(self):
        """
        Exchange current long-lived token for a fresh one.
        Only needed for non-system-user tokens.
        Call this every ~55 days to stay ahead of the 60-day expiry.
        """
        if self.token_type == "system_user":
            logger.info("System user token -- no refresh needed.")
            return self.page_access_token

        url = "https://graph.facebook.com/v21.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": self.page_access_token,
        }
        resp = requests.get(url, params=params)
        data = resp.json()

        if "access_token" in data:
            self.page_access_token = data["access_token"]
            self.config["page_access_token"] = self.page_access_token
            self.config["last_refresh"] = datetime.now().isoformat()
            self.save_config()
            logger.info(f"Token refreshed at {datetime.now().isoformat()}")
            return self.page_access_token
        else:
            logger.error(f"Token refresh failed: {data}")
            return None

    def verify_token(self):
        """Check if the current token is still valid."""
        url = (
            f"https://graph.facebook.com/v21.0/me"
            f"?access_token={self.page_access_token}"
        )
        try:
            resp = requests.get(url, timeout=10)
            return resp.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Token verification error: {e}")
            return False
