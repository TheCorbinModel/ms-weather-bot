import os
import time

COOLDOWN_SECONDS = 15 * 60  # 15 minutes
LAST_POST_FILE = 'last_post_time.txt'

IMMEDIATE_ALERTS = [
    'Tornado Warning',
    'Severe Thunderstorm Warning',
    'Flash Flood Warning',
]

def can_post_alert(alert_type):
    """
    Returns True if the alert can be posted now (immediate or cooldown elapsed), False otherwise.
    Updates the last post time if posting is allowed.
    """
    if alert_type in IMMEDIATE_ALERTS:
        return True
    now = int(time.time())
    last_post = 0
    if os.path.exists(LAST_POST_FILE):
        with open(LAST_POST_FILE, 'r') as f:
            try:
                last_post = int(f.read().strip())
            except Exception:
                last_post = 0
    if now - last_post >= COOLDOWN_SECONDS:
        with open(LAST_POST_FILE, 'w') as f:
            f.write(str(now))
        return True
    return False
