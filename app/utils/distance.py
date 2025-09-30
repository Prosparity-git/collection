import math
from typing import Tuple

def calculate_distance_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) using Haversine formula.
    Returns distance in meters.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    
    return c * r

def is_within_radius(
    point1_lat: float, 
    point1_lon: float, 
    point2_lat: float, 
    point2_lon: float, 
    radius_meters: float = 100
) -> Tuple[bool, float]:
    """
    Check if two GPS points are within specified radius.
    Returns (is_within_radius, actual_distance_in_meters)
    """
    distance = calculate_distance_haversine(point1_lat, point1_lon, point2_lat, point2_lon)
    return distance <= radius_meters, distance
