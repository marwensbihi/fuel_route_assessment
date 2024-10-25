from django.http import JsonResponse
from rest_framework.decorators import api_view
from .services import fetch_route,calculate_fuel_cost,calculate_fuel_stops
from collections import defaultdict


# Caches for storing OSRM responses and location names
cache = defaultdict(dict)
location_cache = defaultdict(str)

@api_view(['POST'])
def get_fuel_stops(request):
    data = request.data
    start_coords = data.get('start_coords')
    finish_coords = data.get('finish_coords')
    max_range_per_tank = data.get('max_range_per_tank', 500)  # Default to 500 miles if not specified

    # Fetch route data
    route_data = fetch_route(start_coords, finish_coords)
    if not route_data:
        return JsonResponse({"error": "Failed to fetch route data"}, status=500)

    # Get start and finish location names directly from the route data
    start_name = route_data['waypoints'][0]['name']
    finish_name = route_data['waypoints'][-1]['name']

    # Calculate fuel stops, total duration, and total distance
    fuel_stops, stop_places_with_coords, total_duration, total_distance = calculate_fuel_stops(route_data, max_range_per_tank)
    total_cost = calculate_fuel_cost(stop_places_with_coords, max_range_per_tank)

    # Return response with calculated information
    return JsonResponse({
        "start_point": {
            "coordinates": start_coords,
            "name": start_name
        },
        "finish_point": {
            "coordinates": finish_coords,
            "name": finish_name
        },
        "fuel_stops": fuel_stops,
        "stop_places": stop_places_with_coords,
        "total_duration": total_duration,
        "total_distance": total_distance,  # Include total distance in the response
        "total_fuel_cost": total_cost,
    }, status=200)

