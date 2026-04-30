import requests
import logging
from datetime import datetime

logger = logging.getLogger("nws_alerts")

NWS_BASE_URL = "https://api.weather.gov"
NWS_HEADERS = {
    "User-Agent": "(MSWeatherBot, msweatherbot@example.com)",
    "Accept": "application/geo+json",
}

# Alert types the bot monitors, with display metadata
ALERT_TYPES = {
    "Tornado Warning":              {"color": "#FF0000", "emoji": "\U0001f32a\ufe0f", "priority": 1},
    "Tornado Watch":                {"color": "#FFFF00", "emoji": "\U0001f32a\ufe0f", "priority": 2},
    "Severe Thunderstorm Warning":  {"color": "#FFA500", "emoji": "\u26c8\ufe0f",     "priority": 3},
    "Severe Thunderstorm Watch":    {"color": "#DB7093", "emoji": "\u26c8\ufe0f",     "priority": 4},
    "Flash Flood Warning":          {"color": "#8B0000", "emoji": "\U0001f30a",       "priority": 5},
    "Flash Flood Watch":            {"color": "#2E8B57", "emoji": "\U0001f30a",       "priority": 6},
    "Flood Warning":                {"color": "#00FF00", "emoji": "\U0001f30a",       "priority": 7},
    "Flood Watch":                  {"color": "#2E8B57", "emoji": "\U0001f30a",       "priority": 8},
    "Winter Storm Warning":         {"color": "#FF69B4", "emoji": "\u2744\ufe0f",     "priority": 9},
    "Winter Storm Watch":           {"color": "#4682B4", "emoji": "\u2744\ufe0f",     "priority": 10},
    "Winter Weather Advisory":      {"color": "#7B68EE", "emoji": "\u2744\ufe0f",     "priority": 11},
    "Heat Advisory":                {"color": "#FF7F50", "emoji": "\U0001f525",       "priority": 12},
    "Excessive Heat Warning":       {"color": "#C71585", "emoji": "\U0001f525",       "priority": 13},
    "Hurricane Warning":            {"color": "#DC143C", "emoji": "\U0001f300",       "priority": 1},
    "Hurricane Watch":              {"color": "#FF00FF", "emoji": "\U0001f300",       "priority": 2},
    "Tropical Storm Warning":       {"color": "#B22222", "emoji": "\U0001f300",       "priority": 3},
    "Tropical Storm Watch":         {"color": "#F08080", "emoji": "\U0001f300",       "priority": 4},
    "Special Weather Statement":    {"color": "#FFE4B5", "emoji": "\u26a0\ufe0f",     "priority": 15},
}

def fetch_mississippi_alerts():
    """Fetch all active weather alerts for Mississippi from the NWS API."""
    url = f"{NWS_BASE_URL}/alerts/active?area=MS"
    try:
        resp = requests.get(url, headers=NWS_HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        alerts = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            alert = {
                "id": props.get("id", ""),
                "event": props.get("event", ""),
                "headline": props.get("headline", ""),
                "description": props.get("description", ""),
                "severity": props.get("severity", ""),
                "urgency": props.get("urgency", ""),
                "certainty": props.get("certainty", ""),
                "areas": props.get("areaDesc", ""),
                "onset": props.get("onset", ""),
                "expires": props.get("expires", ""),
                "sender": props.get("senderName", ""),
                "message_type": props.get("messageType", ""),
                "instruction": props.get("instruction", ""),
            }
            # Extract polygon from geometry if present
            geometry = feature.get("geometry")
            if geometry and geometry.get("type") == "Polygon":
                # NWS polygons are [ [ [lng, lat], ... ] ]
                coords = geometry.get("coordinates", [])
                if coords and isinstance(coords[0], list):
                    alert["polygon"] = [tuple(pt) for pt in coords[0]]
            alerts.append(alert)
        logger.info(f"Fetched {len(alerts)} active alerts for Mississippi")
        return alerts
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching NWS alerts: {e}")
        return []

def filter_significant_alerts(alerts):
    """Filter for watches, warnings, and advisories we care about."""
    significant = []
    for alert in alerts:
        if alert["event"] in ALERT_TYPES:
            alert["meta"] = ALERT_TYPES[alert["event"]]
            significant.append(alert)
    # Sort by priority (most dangerous first)
    significant.sort(key=lambda x: x["meta"]["priority"])
    return significant
