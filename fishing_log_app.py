# Fishing App Data Structure Overview

# Data saved with each location:
# - Name (e.g., '113 Bridge')
# - GPS Coordinates (latitude, longitude)
# - Sub-locations (e.g., 'Below Bridge', 'Pool Between Bridges')
# - Parking Locations (list of (lat, lon) tuples)

# Each fish log entry will now include:
# - Location (linked to saved spots)
# - Specific catch coordinates (lat, lon)
# - Water/fish depth, bait, rigging, catch details
# - Environmental data automatically pulled from APIs

# Users will interactively click on a map to drop a marker and log catches by position

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import streamlit_folium as st_folium
import folium
from geopy.distance import geodesic

# --- Settings ---
LOCATIONS = {
    "113 Bridge": {
        "coordinates": (43.139, -89.387),
        "sub_locations": ["Below Bridge", "Above Bridge", "Pool Between Bridges"],
        "parking": [(43.1392, -89.3875), (43.1388, -89.3862)]
    }
}
USGS_STATION = {
    "05427850": {
        "name": "Yahara River at State Highway 113 at Madison, WI",
        "coordinates": (43.1393, -89.3870),
        "site_id": "05427850"
    }
}
PARAMS = {
    "00060": "Flow (cfs)",
    "00065": "Gage Height (ft)",
    "00010": "Water Temperature (°C)"
}

# --- Data Models ---

# Each outing represents a fishing session
class Outing:
    def __init__(self, location_name, start_time, end_time=None, success_score=None, notes=""):
        # Parse dates if provided as strings
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, "%Y-%m-%d")
        if isinstance(end_time, str) and end_time:
            end_time = datetime.strptime(end_time, "%Y-%m-%d")

        self.location_name = location_name
        self.start_time = start_time
        self.end_time = end_time
        self.success_score = success_score
        self.notes = notes
        self.fish_caught = []  # list of fish dictionaries

    def add_fish(self, fish_data):
        self.fish_caught.append(fish_data)

    def to_dict(self):
    return {
        "Location Name": self.location_name,
        "Start Time": self.start_time.strftime("%Y-%m-%d %I:%M %p"),
        "End Time": self.end_time.strftime("%Y-%m-%d %I:%M %p") if self.end_time else None,
        "Success Score (1–10)": self.success_score,  # Fixed the unterminated string
        "Notes": self.notes,
        "Fish Caught": self.fish_caught
    }

