import requests

def reverse_geocode_nominatim(lat, lon):
    import time
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,  # 10 = city/town, 8 = county
        "addressdetails": 1,
    }
    # Use a descriptive User-Agent with real contact info
    headers = {"User-Agent": "MississippiWeatherBot/1.0 (contact@yourdomain.com)"}
    for attempt in range(3):
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 403:
            # Wait and retry if rate limited or forbidden
            time.sleep(3)
            continue
        resp.raise_for_status()
        address = resp.json().get("address", {})
        # Return all possible city/town/village/county fields
        return {
            "city": address.get("city"),
            "town": address.get("town"),
            "village": address.get("village"),
            "county": address.get("county")
        }
    raise Exception("Nominatim 403 Forbidden after retries. Try again later or use a different User-Agent/email.")


def extract_locations_from_polygon(polygon, max_locations=4):
    """
    Given a polygon (list of (lon, lat)), return up to max_locations unique city/town/county names
    by reverse geocoding the centroid and several distributed points in the polygon.
    """
    if not polygon or len(polygon) < 3:
        return []
    # Calculate centroid
    centroid_lat = sum(pt[1] for pt in polygon) / len(polygon)
    centroid_lon = sum(pt[0] for pt in polygon) / len(polygon)
    points = [(centroid_lat, centroid_lon)]
    # Add up to 3 more points: farthest corners or distributed along the polygon
    n = len(polygon)
    if n > 3:
        # Sample 3 points spaced around the polygon
        for i in range(1, min(max_locations, n)):
            pt = polygon[(i * n) // max_locations]
            points.append((pt[1], pt[0]))
    # Reverse geocode each point, collect unique city/town/village and county names
    seen_cities = set()
    seen_counties = set()
    cities = []
    counties = []
    for lat, lon in points:
        try:
            locs = reverse_geocode_nominatim(lat, lon)
            # Prefer city/town/village for hashtags
            for key in ("city", "town", "village"):
                name = locs.get(key)
                if name and name not in seen_cities:
                    seen_cities.add(name)
                    cities.append(name)
                    break
            county = locs.get("county")
            if county and county not in seen_counties:
                seen_counties.add(county)
                counties.append(county)
            if len(cities) >= max_locations and len(counties) >= max_locations:
                break
        except Exception:
            continue
    # Always return both lists (may be empty)
    return cities[:max_locations], counties[:max_locations]
