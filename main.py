#!/usr/bin/env python3
"""
Mississippi Weather Bot
Automatically monitors NWS alerts for Mississippi, generates
branded graphics, and publishes them to a Facebook Page.
"""

import json
import time
import logging
import os
import signal
import sys
from datetime import datetime

from token_manager import TokenManager
from nws_alerts import fetch_mississippi_alerts, filter_significant_alerts
from graphic_generator import create_alert_graphic
from fb_publisher import compose_post, publish_photo_post, publish_text_post

# ----- Configuration -----
CONFIG_PATH = "config.json"
POSTED_ALERTS_FILE = "posted_alerts.json"
POLL_INTERVAL = 120   # seconds (check every 2 minutes)
MAX_RETRIES = 3
RETRY_DELAY = 30      # seconds between retries

# ----- Logging Setup -----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("weather_bot.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ms_weather_bot")

class MississippiWeatherBot:
    """Core bot class: poll, generate, publish, repeat."""

    def __init__(self):
        self.token_mgr = TokenManager(CONFIG_PATH)
        self.posted_alerts = self._load_posted_alerts()
        self.running = True

        # Handle graceful shutdown (Ctrl+C or kill signal)
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        logger.info("Shutting down gracefully...")
        self.running = False

    def _load_posted_alerts(self):
        """Load the set of already-posted alert IDs from disk."""
        if os.path.exists(POSTED_ALERTS_FILE):
            with open(POSTED_ALERTS_FILE, "r") as f:
                return set(json.load(f))
        return set()

    def _save_posted_alerts(self):
        """Persist posted alert IDs to disk."""
        with open(POSTED_ALERTS_FILE, "w") as f:
            json.dump(list(self.posted_alerts), f)

    def _cleanup_expired_alerts(self, active_alert_ids):
        """Remove expired alert IDs from tracking to prevent
        unbounded growth of the posted_alerts set."""
        self.posted_alerts = self.posted_alerts.intersection(
            active_alert_ids
        )
        self._save_posted_alerts()


    def process_alert(self, alert):
        """Process a single alert: graphic -> compose -> publish."""
        from post_cooldown import can_post_alert
        alert_id = alert["id"]

        if alert_id in self.posted_alerts:
            return  # Already posted

        # Check cooldown/priority logic
        if not can_post_alert(alert["event"]):
            logger.info(f"Cooldown active, skipping post for {alert['event']}")
            return

        logger.info(
            f"New alert: {alert['event']} -- "
            f"{alert.get('headline', 'No headline')}"
        )

        # Step 1: Generate the graphic
        try:
            image_path = create_alert_graphic(alert)
            logger.info(f"Graphic generated: {image_path}")
        except Exception as e:
            logger.error(f"Graphic generation failed: {e}")
            image_path = None

        # Step 2: Compose the post text
        post_text = compose_post(alert)

        # Step 3: Publish to Facebook (with retries)
        for attempt in range(MAX_RETRIES):
            try:
                if image_path and os.path.exists(image_path):
                    post_id = publish_photo_post(
                        self.token_mgr.page_id,
                        self.token_mgr.page_access_token,
                        image_path,
                        post_text,
                    )
                else:
                    post_id = publish_text_post(
                        self.token_mgr.page_id,
                        self.token_mgr.page_access_token,
                        post_text,
                    )

                if post_id:
                    self.posted_alerts.add(alert_id)
                    self._save_posted_alerts()
                    logger.info(
                        f"Posted alert {alert_id} as "
                        f"FB post {post_id}"
                    )
                    # Clean up the graphic file
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                    return

            except Exception as e:
                logger.error(
                    f"Publish attempt {attempt + 1} failed: {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(
            f"Failed to publish alert {alert_id} "
            f"after {MAX_RETRIES} attempts"
        )

    def run(self):
        """Main polling loop."""
        logger.info("Mississippi Weather Bot started!")
        logger.info(
            f"Polling NWS API every {POLL_INTERVAL} seconds..."
        )

        while self.running:
            try:
                # Periodic token check
                if not self.token_mgr.verify_token():
                    logger.warning(
                        "Token validation failed, "
                        "attempting refresh..."
                    )
                    self.token_mgr.refresh_long_lived_token()

                # Fetch and filter Mississippi alerts
                all_alerts = fetch_mississippi_alerts()
                significant = filter_significant_alerts(all_alerts)

                if significant:
                    logger.info(
                        f"Found {len(significant)} "
                        f"significant alerts"
                    )
                    active_ids = {a["id"] for a in significant}
                    self._cleanup_expired_alerts(active_ids)

                    for alert in significant:
                        self.process_alert(alert)
                else:
                    logger.debug(
                        "No significant alerts active "
                        "for Mississippi"
                    )

            except Exception as e:
                logger.error(
                    f"Error in main loop: {e}", exc_info=True
                )

            # Interruptible sleep
            for _ in range(POLL_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Bot stopped.")

if __name__ == "__main__":
    if "--test-post" in sys.argv:
        # Test mode: post a test message to Facebook
        from fb_publisher import publish_text_post
        from token_manager import TokenManager
        print("[TEST MODE] Posting test message to Facebook...")
        token_mgr = TokenManager(CONFIG_PATH)
        # Debug: Print token and page id info
        print("[DEBUG] PAGE_ID:", token_mgr.page_id)
        print("[DEBUG] PAGE_ACCESS_TOKEN (first 10 chars):", str(token_mgr.page_access_token)[:10], "... length:", len(str(token_mgr.page_access_token)))
        test_message = (
            "\u26a0\ufe0f TEST ALERT \u26a0\ufe0f\n"
            "This is a test post from the Mississippi Weather Bot.\n"
            "If you see this, your bot is able to publish to Facebook!\n\n"
            "#Test #MSSevereWx #Mississippi"
        )
        post_id = publish_text_post(
            token_mgr.page_id,
            token_mgr.page_access_token,
            test_message,
        )
        if post_id:
            print(f"[SUCCESS] Test post published! Post ID: {post_id}")
        else:
            print("[ERROR] Test post failed. Check your credentials and permissions.")
    elif "--single-run" in sys.argv:
        bot = MississippiWeatherBot()
        all_alerts = fetch_mississippi_alerts()
        significant = filter_significant_alerts(all_alerts)
        for alert in significant:
            bot.process_alert(alert)
    else:
        bot = MississippiWeatherBot()
        bot.run()
