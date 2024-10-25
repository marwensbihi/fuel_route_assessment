import math
import os, re
import pandas as pd
import requests
from collections import defaultdict  # For efficient location name caching

# Load fuel prices once when the app starts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
fuel_prices_df = pd.read_csv(os.path.join(DATA_DIR, 'fuelprices.csv'))

cache = defaultdict(dict)  # Cache for storing OSRM responses (key: coordinates)
location_cache = defaultdict(str)  # Cache for storing location names (key: coordinates)


def fetch_route(start_coords, finish_coords):
    osrm_api_url = f"http://router.project-osrm.org/route/v1/driving/{start_coords};{finish_coords}?overview=full&geometries=geojson"
    response = requests.get(osrm_api_url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching route: {response.status_code}")
        return None

def calculate_fuel_stops(route_data, max_range_per_tank):
    # Extract total distance and duration directly from the OSRM response
    total_distance = route_data['routes'][0]['distance'] / 1609.34  # Convert meters to miles
    total_duration = route_data['routes'][0]['duration'] / 3600  # Convert seconds to hours
    waypoints = route_data['routes'][0]['geometry']['coordinates']

    stops = []  # List to store stop locations
    current_distance = 0

    # Iterate through the waypoints to decide stop places
    for i in range(1, len(waypoints)):
        # Calculate segment distance directly from OSRM
        segment_distance = haversine(waypoints[i - 1], waypoints[i])  # Optionally, if you want the exact segment distance
        current_distance += segment_distance

        # Check if we should add a stop
        if current_distance >= max_range_per_tank:
            stops.append((waypoints[i][1], waypoints[i][0]))  # Store as (latitude, longitude)
            current_distance = 0  # Reset distance after adding a stop

    stop_places_with_coords = get_location_names_with_coords(stops)
    return len(stops), stop_places_with_coords, total_duration, total_distance

def calculate_fuel_cost(stop_places_with_coords,max_range_per_tank):
    total_cost = 0  # Initialize total cost
    
    # Calculate the mean of all Retail Price values
    overall_mean_price = fuel_prices_df['Retail Price'].mean() 
    
    for place in stop_places_with_coords:
        address = place['name'].split(',')[-1].strip()  # Extract state or location from the stop name
        
        # Check if the address exists in the DataFrame
        matching_rows = fuel_prices_df[fuel_prices_df['Address'].str.contains(address, case=False, na=False)]
        
        if not matching_rows.empty:
            # Sum the Retail Price for the matching rows
            total_cost += matching_rows['Retail Price'].mean() * (max_range_per_tank/10)  # Use mean if there are multiple matches
        else:
            # Use the mean of all Retail Prices if no match is found
            total_cost += overall_mean_price * (max_range_per_tank/10) 
    
    return total_cost

def get_location_names_with_coords(coords_list):
    location_names_with_coords = []
    for coords in coords_list:
        latitude, longitude = coords
        # Use the Nominatim API for reverse geocoding
        google_maps_api_url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
        response = requests.get(google_maps_api_url)
        if response.status_code == 200:
            data = response.json()
            location_names_with_coords.append({
                "name": data.get('display_name', 'Unknown Location'),
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                }
            })
        else:
            location_names_with_coords.append({
                "name": "Unknown Location",
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                }
            })
    return location_names_with_coords

def get_location_name(coords):
    if coords in location_cache:
        return location_cache[coords]

    latitude, longitude = coords.split(',')
    url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        location_name = data.get('display_name', 'Unknown Location')
    else:
        location_name = "Unknown Location"
    
    location_cache[coords] = location_name  # Cache the result
    return location_name

def haversine(coord1, coord2):
    # Calculate the distance between two coordinates using the Haversine formula
    R = 3958.8  # Radius of the Earth in miles
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # Distance in miles

