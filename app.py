import streamlit as st
import folium
import requests
from geopy.geocoders import Nominatim
from shapely.geometry import LineString
import osmnx as ox
from streamlit_folium import st_folium

# Streamlit App Title
st.title("🏞 High Elevation Residential Streets Finder")

# Sidebar settings
st.sidebar.header("Settings")
location_input = st.sidebar.text_input("Enter a city, state:", "Hercules, CA")
ELEVATION_THRESHOLD = st.sidebar.slider("Minimum Elevation (m)", 0, 500, 50)
SEARCH_RADIUS = st.sidebar.slider("Search Radius (m)", 500, 10000, 3000)

# Function to get elevation from Open-Elevation API
def get_elevation(lat, lon):
    url = "https://api.open-elevation.com/api/v1/lookup"
    params = {"locations": f"{lat},{lon}"}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()["results"][0]["elevation"]

# When user clicks the button
if st.sidebar.button("Find Streets"):
    st.write(f"Geocoding {location_input}...")
    geolocator = Nominatim(user_agent="high_elev_finder")
    loc = geolocator.geocode(location_input)
    if not loc:
        st.error("❌ Location not found")
    else:
        center_lat, center_lon = loc.latitude, loc.longitude

        st.write("Downloading residential streets...")
        G = ox.graph_from_point((center_lat, center_lon), dist=SEARCH_RADIUS, network_type='drive')
        res_streets = ox.graph_to_gdfs(G, nodes=False, edges=True)
        res_streets = res_streets[res_streets['highway'].isin(['residential'])]

        st.write("Checking street elevations... this may take a while")
        high_elev_streets = []
        for idx, row in res_streets.iterrows():
            line: LineString = row.geometry
            mid_point = line.interpolate(0.5, normalized=True)
            elev = get_elevation(mid_point.y, mid_point.x)
            if elev >= ELEVATION_THRESHOLD:
                high_elev_streets.append((mid_point.y, mid_point.x, row.get('name', 'Unnamed Street'), elev))

        # Create folium map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
        for lat, lon, name, elev in high_elev_streets:
            folium.Marker(
                location=[lat, lon],
                popup=f"{name} ({elev} m)",
                icon=folium.Icon(color='red', icon='road')
            ).add_to(m)

        st_folium(m, width=725, height=500)

        st.success(f"✅ Found {len(high_elev_streets)} high elevation streets")
