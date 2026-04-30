import requests
import logging

logger = logging.getLogger("fb_publisher")

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Hashtag mappings by alert type
HASHTAG_MAP = {
    "Tornado Warning": (
        "#TornadoWarning #Tornado #SevereWeather "
        "#MSSevereWx #Mississippi #TakeShelter"
    ),
    "Tornado Watch": (
        "#TornadoWatch #Tornado #SevereWeather "
        "#MSSevereWx #Mississippi #StayAlert"
    ),
    "Severe Thunderstorm Warning": (
        "#SevereThunderstorm #SevereWeather "
        "#MSSevereWx #Mississippi #StormWarning"
    ),
    "Severe Thunderstorm Watch": (
        "#SevereThunderstormWatch #SevereWeather "
        "#MSSevereWx #Mississippi"
    ),
    "Flash Flood Warning": (
        "#FlashFlood #FloodWarning #MSSevereWx "
        "#Mississippi #TurnAroundDontDrown"
    ),
    "Flash Flood Watch": (
        "#FlashFloodWatch #Flooding #MSSevereWx #Mississippi"
    ),
    "Flood Warning": (
        "#FloodWarning #Flooding #MSSevereWx #Mississippi"
    ),
    "Flood Watch": (
        "#FloodWatch #Flooding #MSSevereWx #Mississippi"
    ),
    "Winter Storm Warning": (
        "#WinterStorm #WinterWeather #MSSevereWx "
        "#Mississippi #IcyRoads"
    ),
    "Winter Storm Watch": (
        "#WinterStormWatch #WinterWeather #MSSevereWx #Mississippi"
    ),
    "Hurricane Warning": (
        "#Hurricane #HurricaneWarning #MSSevereWx "
        "#Mississippi #TropicalWeather"
    ),
    "Hurricane Watch": (
        "#HurricaneWatch #MSSevereWx #Mississippi #TropicalWeather"
    ),
    "Tropical Storm Warning": (
        "#TropicalStorm #MSSevereWx #Mississippi #TropicalWeather"
    ),
    "Tropical Storm Watch": (
        "#TropicalStormWatch #MSSevereWx #Mississippi #TropicalWeather"
    ),
    "Excessive Heat Warning": (
        "#ExcessiveHeat #HeatWarning #MSSevereWx "
        "#Mississippi #StayHydrated"
    ),
    "Heat Advisory": (
        "#HeatAdvisory #MSSevereWx #Mississippi "
        "#StayHydrated #StayCool"
    ),
}

def compose_post(alert):
    """Create a Facebook-ready post text with hashtags."""
    event = alert["event"]
    emoji = alert.get("meta", {}).get("emoji", "\u26a0\ufe0f")
    areas = alert.get("areas", "Mississippi")
    headline = alert.get("headline", "")
    instruction = alert.get("instruction", "")
    description = alert.get("description", "")

    # Try to get city/county hashtags from alert_post_formatter if available
    try:
        from alert_post_formatter import extract_locations_for_post, build_hashtags
        cities, counties = extract_locations_for_post(alert, max_locations=4)
        location_tags = build_hashtags(alert, cities if cities else counties)
    except Exception:
        location_tags = ""

    lines = []
    lines.append(f"{emoji} {event.upper()} {emoji}")
    lines.append("")

    if headline:
        lines.append(headline)
        lines.append("")

    lines.append(f"\U0001f4cd Areas: {areas}")
    lines.append("")

    onset = alert.get("onset", "")
    expires = alert.get("expires", "")
    if onset and expires:
        from datetime import datetime
        try:
            onset_dt = datetime.fromisoformat(
                onset.replace("Z", "+00:00")
            )
            expires_dt = datetime.fromisoformat(
                expires.replace("Z", "+00:00")
            )
            lines.append(
                f"\u23f0 Valid: {onset_dt.strftime('%b %d, %I:%M %p')} "
                f"-- {expires_dt.strftime('%b %d, %I:%M %p')}"
            )
            lines.append("")
        except ValueError:
            pass

    # Always include WHAT, WHERE, WHEN, IMPACTS (with fallback if missing)
    import re
    key_points = {}
    for key in ["WHAT", "WHERE", "WHEN", "IMPACTS"]:
        m = re.search(rf"\* {key}(.+?)(\n\*|$)", description or '', re.DOTALL)
        if m:
            key_points[key] = m.group(1).strip()
        else:
            key_points[key] = None

    # Fallbacks if missing
    if not key_points["WHAT"]:
        key_points["WHAT"] = alert.get("headline") or alert.get("event")
    if not key_points["WHERE"]:
        key_points["WHERE"] = alert.get("areas") or "Mississippi"
    if not key_points["WHEN"]:
        onset = alert.get("onset", "")
        expires = alert.get("expires", "")
        if onset and expires:
            from datetime import datetime
            try:
                onset_dt = datetime.fromisoformat(onset.replace("Z", "+00:00"))
                expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                key_points["WHEN"] = f"{onset_dt.strftime('%b %d, %I:%M %p')} -- {expires_dt.strftime('%b %d, %I:%M %p')}"
            except Exception:
                key_points["WHEN"] = "Time not specified"
        else:
            key_points["WHEN"] = "Time not specified"
    if not key_points["IMPACTS"]:
        key_points["IMPACTS"] = "Impacts not specified."

    # Add the four key points in order
    lines.append(f"* WHAT: {key_points['WHAT']}")
    lines.append(f"* WHERE: {key_points['WHERE']}")
    lines.append(f"* WHEN: {key_points['WHEN']}")
    lines.append(f"* IMPACTS: {key_points['IMPACTS']}")
    lines.append("")

    if instruction:
        if len(instruction) > 300:
            instruction = instruction[:297] + "..."
        lines.append(f"\u2139\ufe0f {instruction}")
        lines.append("")

    lines.append(
        f"\U0001f4e1 Source: "
        f"{alert.get('sender', 'National Weather Service')}"
    )
    lines.append("")

    # Add only concise hashtags (event, alert type, location, state)
    if location_tags:
        lines.append(location_tags)

    return "\n".join(lines)

def publish_photo_post(page_id, access_token, image_path, message):
    """Publish a photo post with caption to a Facebook Page."""
    url = f"{GRAPH_API_BASE}/{page_id}/photos"

    with open(image_path, "rb") as img_file:
        files = {"source": img_file}
        data = {
            "access_token": access_token,
            "message": message,
        }
        resp = requests.post(url, data=data, files=files)

    result = resp.json()
    if "id" in result:
        logger.info(
            f"Post published successfully! Post ID: {result['id']}"
        )
        return result["id"]
    else:
        logger.error(f"Failed to publish post: {result}")
        return None

def publish_text_post(page_id, access_token, message):
    """Publish a text-only post (fallback if image generation fails)."""
    url = f"{GRAPH_API_BASE}/{page_id}/feed"
    data = {
        "access_token": access_token,
        "message": message,
    }
    resp = requests.post(url, data=data)
    result = resp.json()
    if "id" in result:
        logger.info(f"Text post published! Post ID: {result['id']}")
        return result["id"]
    else:
        logger.error(f"Failed to publish text post: {result}")
        return None
