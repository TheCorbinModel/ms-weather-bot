from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

def create_alert_graphic(alert, output_dir="graphics"):
    """Generate a clean weather alert graphic for Facebook posting."""
    os.makedirs(output_dir, exist_ok=True)

    # Image dimensions (Facebook recommended)
    WIDTH, HEIGHT = 1200, 630

    # Get alert colors and emoji from metadata
    meta = alert.get("meta", {})
    alert_color = meta.get("color", "#FF0000")
    emoji = meta.get("emoji", "\u26a0\ufe0f")

    # Create base image with dark background
    img = Image.new("RGB", (WIDTH, HEIGHT), color="#1a1a2e")
    draw = ImageDraw.Draw(img)

    # ---- Load fonts (fallback to default if unavailable) ----
    try:
        font_large = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
        )
        font_medium = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28
        )
        font_small = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22
        )
        font_brand = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20
        )
    except (OSError, IOError):
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
        font_brand = font_large

    # ---- Header bar (color-coded by alert type) ----
    draw.rectangle([(0, 0), (WIDTH, 100)], fill=alert_color)
    header_text = f"{emoji}  {alert['event'].upper()}"
    draw.text((30, 20), header_text, font=font_large, fill="white")

    # ---- Severity + Urgency line ----
    severity = alert.get("severity", "Unknown")
    urgency = alert.get("urgency", "Unknown")
    badge_text = f"Severity: {severity}  |  Urgency: {urgency}"
    draw.text((30, 120), badge_text, font=font_medium, fill="#e0e0e0")

    # ---- Affected areas (word-wrapped) ----
    areas_text = alert.get("areas", "Mississippi")
    wrapped_areas = _wrap_text(areas_text, font_medium, WIDTH - 60)
    y_pos = 175
    draw.text((30, y_pos), "AFFECTED AREAS:", font=font_small, fill=alert_color)
    y_pos += 35
    for line in wrapped_areas[:4]:  # Limit to 4 lines
        draw.text((30, y_pos), line, font=font_small, fill="#cccccc")
        y_pos += 30

    # ---- Valid time range ----
    y_pos += 15
    onset = _format_time(alert.get("onset", ""))
    expires = _format_time(alert.get("expires", ""))
    if onset and expires:
        time_text = f"Valid: {onset} -- {expires}"
        draw.text((30, y_pos), time_text, font=font_medium, fill="#ffffff")

    # ---- Headline (truncated if needed) ----
    y_pos += 50
    headline = alert.get("headline", "")
    if headline:
        wrapped_headline = _wrap_text(headline, font_small, WIDTH - 60)
        for line in wrapped_headline[:3]:
            draw.text((30, y_pos), line, font=font_small, fill="#aaaaaa")
            y_pos += 28

    # ---- Branding footer ----
    draw.rectangle([(0, HEIGHT - 50), (WIDTH, HEIGHT)], fill="#0d0d1a")
    draw.text(
        (30, HEIGHT - 40),
        "MISSISSIPPI WEATHER ALERTS",
        font=font_brand,
        fill="#666666",
    )
    draw.text(
        (WIDTH - 300, HEIGHT - 40),
        "Source: National Weather Service",
        font=font_brand,
        fill="#666666",
    )

    # ---- Save the image ----
    safe_event = alert["event"].replace(" ", "_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_event}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    img.save(filepath, "PNG")

    return filepath


def _wrap_text(text, font, max_width):
    """Simple word-wrap helper for Pillow text rendering."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        if bbox[2] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def _format_time(iso_string):
    """Format an ISO 8601 timestamp to a human-readable string."""
    if not iso_string:
        return ""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %I:%M %p %Z")
    except (ValueError, TypeError):
        return iso_string
