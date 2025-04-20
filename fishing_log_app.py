
# Fishing App Data Structure Overview

# Data saved with each location:
# - Name (e.g., '113 Bridge')
# - GPS Coordinates (latitude, longitude)
# - Sub-locations (e.g., 'Below Bridge', 'Pool Between Bridges')

# User-defined for each fishing log entry:
# - List: Location names and sub-locations
# - Area type (Channel, Hold, Flat, Drop Off)
# - Water Type (Channel, Near Channel, Slack)
# - Position in Water Body (Shore, Transition, Middle)
# - Water Depth (ft)
# - Fish Depth (ft)
# - Shore or Boat
# - Parking Lot or Boat Launch Used
# - Manual Success Score (1–10)
# - Notes (optional in CSV)

# Automatically pulled for each log entry (by date/location):
# - USGS data (flow, gage height, water temperature)
# - Calculated USGS trends (1-day change, 3-day rolling average)
# - Weather data (air temperature, humidity, pressure, wind speed/direction)

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import openmeteo_requests
from retry_requests import retry

# --- Settings ---
LOCATIONS = {
    "113 Bridge": {
        "coordinates": (43.139, -89.387),
        "sub_locations": ["Below Bridge", "Above Bridge", "Pool Between Bridges"]
    },
    "Cherokee Marsh": {
        "coordinates": (43.157, -89.384),
        "sub_locations": ["West Shore", "Outlet Bay", "Lily Pads"]
    }
}
PARAMS = {
    "00060": "Flow (cfs)",
    "00065": "Gage Height (ft)",
    "00010": "Water Temperature (°C)"
}

def get_user_settings():
    st.sidebar.header("⚙️ Settings")
    show_errors = st.sidebar.checkbox("Show error messages when data fails to load", value=True)
    return {"show_errors": show_errors}

# --- Functions ---
def fetch_usgs_data(site_id, days=7, show_errors=True):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_id}&startDT={start_date.strftime('%Y-%m-%d')}&endDT={end_date.strftime('%Y-%m-%d')}&parameterCd=00060,00065,00010&siteStatus=all"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        timeseries = data['value']['timeSeries']
        df_list = []

        for series in timeseries:
            variable = series['variable']['variableCode'][0]['value']
            name = PARAMS.get(variable, variable)
            values = series['values'][0]['value']
            df = pd.DataFrame(values)
            df['dateTime'] = pd.to_datetime(df['dateTime'])
            df[name] = pd.to_numeric(df['value'], errors='coerce')
            df = df[['dateTime', name]]
            df_list.append(df.set_index('dateTime'))

        final_df = pd.concat(df_list, axis=1).reset_index()
        return final_df
    except Exception as e:
        if show_errors:
            st.error(f"Failed to fetch USGS data: {e}")
        return pd.DataFrame()

def calculate_trends(df):
    trend_df = df.copy()
    trend_df = trend_df.sort_values('dateTime')
    for col in PARAMS.values():
        if col in trend_df.columns:
            trend_df[f'{col} 1d Change'] = trend_df[col].diff()
            trend_df[f'{col} 3d Rolling Avg'] = trend_df[col].rolling(window=3).mean()
    return trend_df

def fetch_weather_data(latitude, longitude, timezone="America/Chicago", show_errors=True):
    try:
        client = openmeteo_requests.Client(retry_strategy=retry())
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ["temperature_2m", "relative_humidity_2m", "surface_pressure", "wind_speed_10m", "wind_direction_10m"],
            "timezone": timezone
        }
        response = client.get(url, params=params)
        data = response.json()
        hourly = pd.DataFrame(data["hourly"])
        hourly["time"] = pd.to_datetime(hourly["time"])
        return hourly
    except Exception as e:
        if show_errors:
            st.error(f"Failed to fetch weather data: {e}")
        return pd.DataFrame()

# --- Streamlit Interface ---
settings = get_user_settings()

st.set_page_config(page_title="Fishing Forecast App", layout="wide")
st.title("🎣 Fishing Success Predictor")

st.markdown("This app pulls live water condition data from the Yahara River (USGS Station 05427850) and calculates trends to help you predict fishing success. Weather conditions are included too.")

# Select location and sub-location
st.subheader("📍 Select Fishing Location")
location_name = st.selectbox("Choose a fishing location:", list(LOCATIONS.keys()))
sub_location = st.selectbox("Choose a sub-location (optional):", LOCATIONS[location_name]["sub_locations"])
coords = LOCATIONS[location_name]["coordinates"]

# Additional location details
area_type = st.selectbox("Area Type:", ["Channel", "Hold", "Flat", "Drop Off"])
water_type = st.selectbox("Water Type:", ["Channel", "Near Channel", "Slack"])
position = st.selectbox("Position in Water Body:", ["Shore", "Transition", "Middle"])
shore_or_boat = st.selectbox("Fishing Method:", ["Shore", "Boat"])
access_point = st.text_input("Parking Lot or Boat Launch Used:")
water_depth = st.number_input("Water Depth (ft):", min_value=0.0, step=0.1)
fish_depth = st.number_input("Fish Depth (ft):", min_value=0.0, step=0.1)

# Fetch and process USGS data
with st.spinner("Fetching USGS data..."):
    raw_df = fetch_usgs_data("05427850", days=7, show_errors=settings["show_errors"])
    trend_df = calculate_trends(raw_df)

if not trend_df.empty:
    st.subheader("📊 Water Condition Trends")
    st.dataframe(trend_df.tail(15), use_container_width=True)

# Fetch and display weather data
st.subheader("🌦️ Recent Weather Conditions")
with st.spinner("Fetching weather data..."):
    weather_df = fetch_weather_data(*coords, show_errors=settings["show_errors"])
    if not weather_df.empty:
        st.dataframe(weather_df.tail(15), use_container_width=True)

# Upload fishing log
st.subheader("📂 Upload Your Fishing Log")
log_file = st.file_uploader("Upload CSV", type=["csv"])

if log_file is not None:
    user_log = pd.read_csv(log_file)
    st.write("Your Fishing Log:")
    st.dataframe(user_log)

    st.subheader("🎯 Rate Your Trip Success")
    selected_row = st.selectbox("Select a row to rate (by index):", user_log.index)
    if selected_row is not None:
        score = st.slider("Success Score (1 = poor, 10 = excellent)", 1, 10, 5)
        user_log.loc[selected_row, "Success Score (1–10)"] = score
        st.success(f"Recorded success score of {score} for row {selected_row}.")

# --- Add new log entry ---
st.subheader("➕ Add New Fishing Log Entry")
if st.button("Add This Entry to Log"):
    now = datetime.now()
    new_entry = {
        "Date": now.strftime("%Y-%m-%d"),
        "Time": now.strftime("%I:%M %p"),
        "Location Name": location_name,
        "Sub-location": sub_location,
        "Area Type": area_type,
        "Water Type": water_type,
        "Position": position,
        "Fishing Method": shore_or_boat,
        "Access Point": access_point,
        "Water Depth (ft)": water_depth,
        "Fish Depth (ft)": fish_depth,
        "Success Score (1–10)": score if log_file is not None else None,
        "Notes": "",
        "Latitude": coords[0],
        "Longitude": coords[1]
    }

    if log_file is not None:
        updated_log = pd.concat([user_log, pd.DataFrame([new_entry])], ignore_index=True)
    else:
        updated_log = pd.DataFrame([new_entry])

    st.success("🎣 New fishing log entry added.")
    st.dataframe(updated_log)

    csv = updated_log.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Updated Log",
        data=csv,
        file_name="updated_fishing_log.csv",
        mime="text/csv"
    )

# Placeholder for prediction (coming soon)
st.subheader("🔮 Prediction Coming Soon")
st.info("In the next version, this app will use environmental data, weather, and your log to predict catch likelihood!")
