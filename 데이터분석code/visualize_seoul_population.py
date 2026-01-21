import pandas as pd
import folium
import json
import os
import requests
from datetime import datetime, timedelta

# Configuration
DATA_PATH = 'seoul_floating_pop_raw3.csv'
OUTPUT_DIR = 'population_maps'
GEOJSON_URL = 'https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json'

# Broadcast dates (Strings for easy handling, but we will convert)
BROADCAST_DATES = [
    "2025-12-16",
    "2025-12-23",
    "2025-12-30",
    "2026-01-06",
    "2026-01-13"
]

def load_data(file_path):
    """Loads and preprocesses the floating population data."""
    print("Loading data...")
    # Read only necessary columns to save memory if file is large
    df = pd.read_csv(file_path, usecols=['SENSING_TIME', 'AUTONOMOUS_DISTRICT', 'VISITOR_COUNT'])
    
    # Convert SENSING_TIME to datetime
    df['SENSING_TIME'] = pd.to_datetime(df['SENSING_TIME'])
    
    # Extract date part for daily aggregation
    df['DATE'] = df['SENSING_TIME'].dt.date
    return df

def aggregate_by_date_and_gu(df, target_dates):
    """Aggregates visitor counts by Date and Autonomous District."""
    print("Aggregating data...")
    # Filter for only the dates we care about to speed up
    mask = df['DATE'].isin(target_dates)
    filtered_df = df[mask]
    
    # Group by Date and District, sum visitor counts
    aggregated = filtered_df.groupby(['DATE', 'AUTONOMOUS_DISTRICT'])['VISITOR_COUNT'].sum().reset_index()
    return aggregated

def create_comparison_map(agg_df, base_date_str, geo_data):
    """Creates a Folium map comparing -7 days and +7 days for a given broadcast date."""
    base_date = datetime.strptime(base_date_str, "%Y-%m-%d").date()
    before_date = base_date - timedelta(days=7)
    after_date = base_date + timedelta(days=7)
    
    print(f"Generating map for Base: {base_date}, Before: {before_date}, After: {after_date}")

    # Create base map centered on Seoul
    m = folium.Map(location=[37.5502, 126.982], zoom_start=11, tiles='cartodbpositron')

    # Helper to add layer
    def add_layer(target_date, layer_name, color_scheme):
        day_data = agg_df[agg_df['DATE'] == target_date]
        if day_data.empty:
            print(f"  Warning: No data found for {target_date} ({layer_name})")
            return

        # Create Choropleth
        choropleth = folium.Choropleth(
            geo_data=geo_data,
            data=day_data,
            columns=['AUTONOMOUS_DISTRICT', 'VISITOR_COUNT'],
            key_on='feature.properties.name',
            fill_color=color_scheme,
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=f'Daily Floating Population ({target_date})',
            name=layer_name,
            highlight=True
        )
        
        # Add tooltips
        choropleth.geojson.add_child(
            folium.features.GeoJsonTooltip(['name'], labels=False)
        )
        choropleth.add_to(m)

    # Add Before Layer (Blue-ish)
    add_layer(before_date, f"7 Days Before ({before_date})", 'BuPu')
    
    # Add After Layer (Red-ish)
    add_layer(after_date, f"7 Days After ({after_date})", 'YlOrRd')

    # Add Layer Control to toggle
    folium.LayerControl().add_to(m)
    
    return m

def main():
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load GeoJSON
    print(f"Fetching GeoJSON from {GEOJSON_URL}...")
    geo_data = requests.get(GEOJSON_URL).json()
    
    # Calculate all necessary dates to filter
    all_target_dates = set()
    for d_str in BROADCAST_DATES:
        d = datetime.strptime(d_str, "%Y-%m-%d").date()
        all_target_dates.add(d - timedelta(days=7))
        all_target_dates.add(d + timedelta(days=7))
        
    # Load Data
    if not os.path.exists(DATA_PATH):
        print(f"Error: Data file {DATA_PATH} not found.")
        return

    df = load_data(DATA_PATH)
    
    # Aggregate
    agg_df = aggregate_by_date_and_gu(df, all_target_dates)
    
    # Generate Maps
    for broadcast_date in BROADCAST_DATES:
        m = create_comparison_map(agg_df, broadcast_date, geo_data)
        
        # Save map
        filename = f"{OUTPUT_DIR}/population_comparison_{broadcast_date.replace('-', '')}.html"
        m.save(filename)
        print(f"Saved map to {filename}")

if __name__ == "__main__":
    main()
