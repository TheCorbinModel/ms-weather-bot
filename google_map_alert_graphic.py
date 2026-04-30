# NWS event type to color mapping (hex)
NWS_EVENT_COLORS = {
    'Tornado Warning': '#FF0000',
    'Tornado Watch': '#FF9900',
    'Severe Thunderstorm Warning': '#FFCC00',
    'Severe Thunderstorm Watch': '#FFCC00',
    'Flash Flood Warning': '#00FF00',
    'Flood Warning': '#00FF00',
    'Flood Advisory': '#00FF00',
    'Flood Watch': '#00FF00',
    'Winter Storm Warning': '#00BFFF',
    'Winter Weather Advisory': '#00BFFF',
    'Blizzard Warning': '#00BFFF',
    'Ice Storm Warning': '#00BFFF',
    'Heat Advisory': '#FF6600',
    'Excessive Heat Warning': '#FF6600',
    'Wind Advisory': '#CCCCCC',
    'High Wind Warning': '#CCCCCC',
    'Red Flag Warning': '#FF3366',
    'Fire Weather Watch': '#FF3366',
    'Hurricane Warning': '#FF00FF',
    'Hurricane Watch': '#FF00FF',
    'Tropical Storm Warning': '#FF00FF',
    'Tropical Storm Watch': '#FF00FF',
    'Special Weather Statement': '#999999',
    'Dense Fog Advisory': '#999999',
    'Freeze Warning': '#3399FF',
    'Frost Advisory': '#3399FF',
    'Freeze Watch': '#3399FF',
    'Coastal Flood Warning': '#00FF99',
    'Coastal Flood Advisory': '#00FF99',
    'Coastal Flood Watch': '#00FF99',
    'Storm Surge Warning': '#FF00FF',
    'Storm Surge Watch': '#FF00FF',
    # Add more as needed
}

import os
import math
from dotenv import load_dotenv
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# --- CONFIG ---
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "YOUR_API_KEY_HERE")
MAP_WIDTH = 960
MAP_HEIGHT = 504
GOOGLE_MAP_WIDTH = 640
GOOGLE_MAP_HEIGHT = 640
LOGO_PATH = "delta_boys_logo.png"

# Helper to get map center and zoom to fit polygon
def get_center_and_zoom(polygon, img_width, img_height):
    lats = [pt[1] for pt in polygon]
    lngs = [pt[0] for pt in polygon]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)
    # Center on polygon centroid for better visual balance
    centroid_lat = sum(lats) / len(lats)
    centroid_lng = sum(lngs) / len(lngs)
    # Reduce padding for a closer zoom, but keep some context
    lat_pad = (max_lat - min_lat) * 1.2 or 0.3
    lng_pad = (max_lng - min_lng) * 1.2 or 0.3
    min_lat -= lat_pad
    max_lat += lat_pad
    min_lng -= lng_pad
    max_lng += lng_pad

    # Minimum zoom-out: if the calculated zoom is too high (too close), force a lower zoom (further out)
    # Clamp zoom: never zoom in closer than MAX_ZOOM_IN, never zoom out farther than MIN_ZOOM_OUT
    MIN_ZOOM_OUT = 4  # farthest out allowed
    MAX_ZOOM_IN = 12  # closest in allowed
    # Calculate zoom to fit bounds (approximate)
    def lat_rad(lat):
        s = math.sin(lat * math.pi / 180)
        return math.log((1 + s) / (1 - s)) / 2
    def zoom(map_px, world_px, fraction):
        return int(math.floor(math.log(map_px / world_px / fraction) / math.log(2)))
    WORLD_DIM = {'height': 256, 'width': 256}
    ZOOM_MAX = 21
    lat_fraction = (lat_rad(max_lat) - lat_rad(min_lat)) / math.pi
    lng_diff = max_lng - min_lng
    lng_fraction = ((lng_diff + 360) if lng_diff < 0 else lng_diff) / 360
    lat_zoom = zoom(img_height, WORLD_DIM['height'], lat_fraction) if lat_fraction > 0 else ZOOM_MAX
    lng_zoom = zoom(img_width, WORLD_DIM['width'], lng_fraction) if lng_fraction > 0 else ZOOM_MAX
    zoom_level = min(lat_zoom, lng_zoom, ZOOM_MAX)
    # Zoom in a tiny bit more
    zoom_level += 1
    zoom_level = max(zoom_level, MIN_ZOOM_OUT)
    zoom_level = min(zoom_level, MAX_ZOOM_IN)
    return centroid_lat, centroid_lng, zoom_level

def create_google_map_alert_graphic(alert, output_dir="graphics"):
    os.makedirs(output_dir, exist_ok=True)
    polygon = alert["polygon"]  # [(lng, lat), ...]
    event = alert.get("event", "Alert")
    # Use alert color if provided, otherwise use NWS standard color for event
    event_type = alert.get("event", "Alert")
    color = alert.get("color")
    if not color:
        color = NWS_EVENT_COLORS.get(event_type, "#FF0000")
    headline = alert.get("headline", "")
    location = alert.get("areas", "Mississippi")

    # Get map center and zoom to fit polygon, or use manual override
    manual_zoom = alert.get("zoom")
    center_lat, center_lng, best_zoom = get_center_and_zoom(polygon, GOOGLE_MAP_WIDTH, GOOGLE_MAP_HEIGHT)
    if manual_zoom is not None:
        best_zoom = int(manual_zoom)
    center = f"{center_lat},{center_lng}"

    # Build Google Static Maps API URL (use calculated zoom)
    # Add style for more detail (labels, POIs, roads, etc.)
    style = (
        "&style=feature:poi|visibility:on"
        "&style=feature:road|visibility:on"
        "&style=feature:administrative|visibility:on"
        "&style=feature:landscape|visibility:on"
        "&style=feature:transit|visibility:on"
        "&style=feature:water|visibility:on"
        "&style=feature:all|element:labels|visibility:on"
    )
    url = (
        f"https://maps.googleapis.com/maps/api/staticmap?center={center}"
        f"&zoom={best_zoom}&size={GOOGLE_MAP_WIDTH}x{GOOGLE_MAP_HEIGHT}&maptype=roadmap&scale=2{style}&key={GOOGLE_MAPS_API_KEY}"
    )
    response = requests.get(url)
    response.raise_for_status()
    map_img = Image.open(BytesIO(response.content)).convert("RGBA")
    # Resize to output size
    map_img = map_img.resize((MAP_WIDTH, MAP_HEIGHT), Image.LANCZOS)

    # Adjust for top bar: center polygon in the area below the bar
    bar_height = 60  # Reduced from 120
    overlay = Image.new("RGBA", map_img.size)
    draw = ImageDraw.Draw(overlay)
    import math
    TILE_SIZE = 256
    def latlng_to_pixel_google(lat, lng, zoom, map_width, map_height, center_lat, center_lng):
        # Google Static Maps: pixel coordinates relative to top-left
        def lat_to_y(lat):
            siny = math.sin(lat * math.pi / 180)
            y = 0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)
            return y
        def lng_to_x(lng):
            x = (lng + 180) / 360
            return x
        scale = 2 ** zoom
        world_px = TILE_SIZE * scale
        center_x = lng_to_x(center_lng) * world_px
        center_y = lat_to_y(center_lat) * world_px
        x = lng_to_x(lng) * world_px
        y = lat_to_y(lat) * world_px
        px = x - center_x + (map_width / 2)
        py = y - center_y + (map_height / 2)
        return int(px), int(py)

    # Ensure coordinates are (lat, lng) for Google Maps
    pixel_poly = [latlng_to_pixel_google(pt[1], pt[0], best_zoom, MAP_WIDTH, MAP_HEIGHT, center_lat, center_lng) for pt in polygon]

    # No debug bounding box; use full precision for coordinates
    # Fill polygon with more transparent color, then draw a much bolder outline
    fill_color = color + "40" if len(color) == 7 else color  # more transparent
    draw.polygon(pixel_poly, fill=fill_color)
    draw.line(pixel_poly + [pixel_poly[0]], fill=color, width=3, joint="curve")

    # Composite overlay onto map
    out_img = Image.alpha_composite(map_img, overlay)

    # Draw bold top bar
    # Top bar: shorter, bold centered text
    bar = Image.new("RGBA", (MAP_WIDTH, bar_height), color)
    out_img.paste(bar, (0, 0), bar)
    draw = ImageDraw.Draw(out_img)
    bar_text = f"{event.upper()} - {location.upper()}"
    # Auto-shrink font to fit bar with padding
    max_font_size = 40
    min_font_size = 18
    horizontal_padding = 30
    font = None
    for font_size in range(max_font_size, min_font_size - 1, -2):
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
        try:
            bbox = draw.textbbox((0, 0), bar_text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            text_w, text_h = font.getsize(bar_text)
        if text_w <= MAP_WIDTH - 2 * horizontal_padding:
            break
    x = max((MAP_WIDTH - text_w) // 2, horizontal_padding)
    y = (bar_height - text_h) // 2
    draw.text((x, y), bar_text, font=font, fill="white")

    # Add logo in bottom right, slightly larger for better visibility
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_width = 100
        logo_height = int(logo.size[1] * (logo_width / logo.size[0]))
        logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
        out_img.paste(logo, (MAP_WIDTH - logo_width - 30, MAP_HEIGHT - logo_height - 30), logo)
    except Exception as e:
        print(f"[WARN] Could not add logo: {e}")

    # No border

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"googlemap_{event.replace(' ', '_').lower()}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    out_img.convert("RGB").save(filepath, "PNG")
    return filepath

def test_google_map_alert_graphic():
    sample_alert = {
        "event": "Tornado Warning",
        "headline": "Tornado Warning for Central Mississippi",
        "areas": "Central Mississippi",
        "polygon": [
            (-90.5, 32.5), (-90.2, 32.7), (-90.0, 32.4), (-90.3, 32.2), (-90.5, 32.5)
        ],
        "color": "#FF0000"
    }
    path = create_google_map_alert_graphic(sample_alert)
    print(f"Test Google Map graphic saved to: {path}")


if __name__ == "__main__":
    test_google_map_alert_graphic()

# Test function
def test_google_map_alert_graphic():
    sample_alert = {
        "event": "Tornado Warning",
        "headline": "Tornado Warning for Central Mississippi",
        "polygon": [
            (-90.5, 32.5), (-90.2, 32.7), (-90.0, 32.4), (-90.3, 32.2), (-90.5, 32.5)
        ],
        "color": "#FF0000"
    }
    path = create_google_map_alert_graphic(sample_alert)
    print(f"Test Google Map graphic saved to: {path}")

if __name__ == "__main__":
    test_google_map_alert_graphic()
