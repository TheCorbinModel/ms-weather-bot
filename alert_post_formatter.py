import re
from reverse_geocode import extract_locations_from_polygon

def extract_cities_from_text(text):
    # Simple regex for capitalized words (city/town names)
    city_candidates = re.findall(r'\b[A-Z][a-z]+\b', text)
    # Remove common non-city words
    blacklist = set([
        'River', 'Flood', 'Warning', 'Mississippi', 'Tombigbee', 'Buttahatchie', 'L', 'D', 'National', 'Weather', 'Service', 'Memphis', 'TN', 'WHAT', 'WHERE', 'WHEN', 'IMPACTS', 'ADDITIONAL', 'DETAILS', 'Forecast', 'Stage', 'Feet', 'Road', 'Bank', 'Low', 'Land', 'Flooding', 'Area', 'Statement', 'Issued', 'Details', 'Activity', 'Recent', 'Maximum', 'Ending', 'Wednesday', 'Morning', 'Evening', 'Monday', 'Sunday', 'Saturday', 'Including', 'Bigbee', 'Amory', 'Aberdeen', 'Fulton', 'Columbus', 'AFB', 'Hamilton', 'Gatman', 'Splunge', 'Lackey', 'Westville', 'Athens', 'Hatley', 'Smithville', 'Detroit', 'Vernon', 'Sulligent', 'Beaverton', 'Guin', 'Prairie', 'Egypt', 'Darracott', 'Whites', 'Kolola', 'Springs', 'Caledonia', 'Shannon', 'Carolina', 'Pine', 'Grove',
        'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])
    cities = [c for c in city_candidates if c not in blacklist]
    seen = set()
    result = []
    for c in cities:
        if c not in seen:
            seen.add(c)
            result.append(c)
        if len(result) == 3:
            break
    return result

def extract_locations_for_post(alert, max_locations=4):
    """
    Returns a tuple: (city_list, county_list)
    - City/town/village: from reverse geocoding the polygon (preferred)
    - County: from 'areas' field (always available)
    - Fallback: extract from text if needed
    """
    # Parse counties from 'areas' field (e.g., 'Monroe, MS; Marshall, MS; Union, MS')
    areas = alert.get('areas', '')
    counties = []
    if areas:
        for part in areas.split(';'):
            county = part.strip().split(',')[0]
            if county and county not in counties:
                counties.append(county)
    # Try to get cities/towns from polygon
    polygon = alert.get('polygon')
    cities = []
    if polygon:
        try:
            cities, _ = extract_locations_from_polygon(polygon, max_locations=max_locations)
        except Exception:
            pass
    # Fallback: extract from text if no cities found
    if not cities:
        desc = alert.get('description', '') + ' ' + alert.get('headline', '')
        cities = extract_cities_from_text(desc)
    return cities, counties

def build_hashtags(alert, locations, state="Mississippi"):
    # Only include event type, alert type, and state (no city/county/location hashtags)
    event_words = alert.get('event', '').split()
    tags = []
    if event_words:
        tags.append(f"#{event_words[0]}")  # e.g., #Flood
        if len(event_words) > 1:
            tags.append(f"#{event_words[1]}")  # e.g., #Warning or #Watch
    tags.append(f"#{state}")
    return ' '.join(tags)


def extract_locations_for_post(alert, max_locations=4):
    """
    Returns a tuple: (city_list, county_list)
    Prefer extracting up to max_locations city/town/village from the alert's polygon using reverse geocoding.
    Always also extract counties. Fallback to text-based city extraction if no polygon or geocoding fails.
    """
    polygon = alert.get('polygon')
    if polygon:
        try:
            cities, counties = extract_locations_from_polygon(polygon, max_locations=max_locations)
            if not cities:
                # Fallback: extract from text
                desc = alert.get('description', '') + ' ' + alert.get('headline', '')
                cities = extract_cities_from_text(desc)
            return cities, counties
        except Exception:
            pass
    # Fallback: extract from text
    desc = alert.get('description', '') + ' ' + alert.get('headline', '')
    cities = extract_cities_from_text(desc)
    return cities, []


def build_hashtags(alert, locations, state="Mississippi"):
    event_type = alert.get('event', '').split()[0]  # e.g., 'Flood'
    alert_type = alert.get('event', '').split()[-1]  # e.g., 'Warning'
    tags = [f"#{event_type}", f"#{alert_type}"]
    tags += [f"#{loc.replace(' ', '')}" for loc in locations]
    tags.append(f"#{state}")
    return ' '.join(tags)

    """
    Returns a tuple: (city_list, county_list)
    Prefer extracting up to max_locations city/town/village from the alert's polygon using reverse geocoding.
    Always also extract counties. Fallback to text-based city extraction if no polygon or geocoding fails.
    """
    polygon = alert.get('polygon')
    if polygon:
        try:
            cities, counties = extract_locations_from_polygon(polygon, max_locations=max_locations)
            if not cities:
                # Fallback: extract from text
                desc = alert.get('description', '') + ' ' + alert.get('headline', '')
                cities = extract_cities_from_text(desc)
            return cities, counties
        except Exception:
            pass
    # Fallback: extract from text
    desc = alert.get('description', '') + ' ' + alert.get('headline', '')
    cities = extract_cities_from_text(desc)
    return cities, []

# Example usage:
# alert = {...}  # from NWS
# cities = extract_cities_from_text(alert['description'] + ' ' + alert['headline'])
# hashtags = build_hashtags(alert, cities)
# print(hashtags)
