import matplotlib.pyplot as plt
from shapely.geometry import Polygon, MultiPolygon
import geopandas as gpd
import os
from datetime import datetime

# NWS color mapping example (expand as needed)
NWS_COLORS = {
    "Tornado Warning": "#FF0000",
    "Severe Thunderstorm Warning": "#FFA500",
    "Flood Warning": "#00FF00",
    "default": "#0000FF"
}

# Simple Mississippi boundary (approximate, for demo)
MS_BOUNDS = [
    [(-91.655009, 34.996052), (-88.097888, 34.891641), (-88.099322, 30.147789), (-91.636787, 30.997536), (-91.655009, 34.996052)]
]

def create_alert_map_graphic(alert, output_dir="graphics"):
    os.makedirs(output_dir, exist_ok=True)
    
    # Get alert polygon (GeoJSON-style coordinates)
    polygon_coords = alert.get("polygon")
    if not polygon_coords:
        raise ValueError("Alert does not contain a polygon.")
    
    alert_type = alert.get("event", "default")
    color = NWS_COLORS.get(alert_type, NWS_COLORS["default"])
    
    # Create Mississippi boundary polygon
    ms_poly = Polygon(MS_BOUNDS[0])
    ms_gdf = gpd.GeoDataFrame(geometry=[ms_poly], crs="EPSG:4326")
    
    # Create alert polygon
    alert_poly = Polygon(polygon_coords)
    alert_gdf = gpd.GeoDataFrame(geometry=[alert_poly], crs="EPSG:4326")
    
    # Plot
    fig, ax = plt.subplots(figsize=(8, 8))
    ms_gdf.boundary.plot(ax=ax, color="black", linewidth=2)
    ms_gdf.plot(ax=ax, color="#f0f0f0", alpha=0.5)
    alert_gdf.plot(ax=ax, color=color, alpha=0.6, edgecolor="black")
    
    ax.set_title(f"{alert_type} - {alert.get('headline', '')}", fontsize=14)
    ax.set_axis_off()
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"map_{alert_type.replace(' ', '_').lower()}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    return filepath

# Test function
def test_create_alert_map_graphic():
    sample_alert = {
        "event": "Tornado Warning",
        "headline": "Tornado Warning for Central Mississippi",
        "polygon": [
            (-90.5, 32.5), (-90.2, 32.7), (-90.0, 32.4), (-90.3, 32.2), (-90.5, 32.5)
        ]
    }
    path = create_alert_map_graphic(sample_alert)
    print(f"Test map graphic saved to: {path}")

if __name__ == "__main__":
    test_create_alert_map_graphic()
