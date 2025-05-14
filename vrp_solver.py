import numpy as np
import math
import requests
import streamlit as st

def haversine_distance(coord1, coord2):
    """Calculate Haversine distance (km) between two (lat, lon) coordinates."""
    lat1, lon1 = map(math.radians, coord1)
    lat2, lon2 = map(math.radians, coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    R = 6371  # Earth radius in km
    return c * R

@st.cache_data
def get_osrm_distance(start_coord, end_coord):
    """Fetch road-based distance (km) from OSRM API."""
    if not (-90 <= start_coord[0] <= 90 and -180 <= start_coord[1] <= 180 and
            -90 <= end_coord[0] <= 90 and -180 <= end_coord[1] <= 180):
        st.warning(f"Invalid coordinates for distance: {start_coord} to {end_coord}")
        print(f"Invalid coordinates: {start_coord} to {end_coord}")
        return haversine_distance(start_coord, end_coord)  # Fallback

    url = f"http://router.project-osrm.org/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=false"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("routes"):
            distance = data["routes"][0]["distance"] / 1000  # Convert meters to km
            print(f"OSRM distance from {start_coord} to {end_coord}: {distance:.2f} km")
            return distance
        else:
            print(f"OSRM no route found for {start_coord} to {end_coord}: {data.get('message', 'No message')}")
            st.warning(f"No road route found for {start_coord} to {end_coord}. Using straight-line distance.")
            return haversine_distance(start_coord, end_coord)  # Fallback
    except requests.RequestException as e:
        print(f"OSRM API error for {start_coord} to {end_coord}: {e}")
        st.warning(f"OSRM API failed for {start_coord} to {end_coord}. Using straight-line distance.")
        return haversine_distance(start_coord, end_coord)  # Fallback

def create_distance_matrix(depot_coords, customer_coords):
    """Create distance matrix using OSRM road-based distances."""
    n = len(customer_coords) + 1  # Include depot
    dist_matrix = np.zeros((n, n))
    
    # Depot to customers (index 0 is depot)
    for i in range(1, n):
        dist_matrix[0, i] = dist_matrix[i, 0] = get_osrm_distance(depot_coords, customer_coords[i-1])
    
    # Customer to customer
    for i in range(1, n):
        for j in range(i + 1, n):
            dist_matrix[i, j] = dist_matrix[j, i] = get_osrm_distance(customer_coords[i-1], customer_coords[j-1])
    
    return dist_matrix

def clarke_wright(depot_coords, customer_coords, customer_demands, vehicle_capacity, num_vehicles):
    """Clarke-Wright savings algorithm with road-based distances."""
    n_customers = len(customer_coords)
    if n_customers == 0:
        return [], np.zeros((1, 1)), []

    # Create distance matrix
    dist_matrix = create_distance_matrix(depot_coords, customer_coords)
    
    # Initialize routes: each customer has a direct route to/from depot
    routes = [[i + 1] for i in range(n_customers)]  # 1-based indexing for customers
    route_loads = customer_demands.copy()
    
    # Calculate savings: s(i,j) = d(0,i) + d(0,j) - d(i,j)
    savings = []
    for i in range(1, n_customers + 1):
        for j in range(i + 1, n_customers + 1):
            s = dist_matrix[0, i] + dist_matrix[0, j] - dist_matrix[i, j]
            savings.append((s, i, j))
    savings.sort(reverse=True)  # Sort by descending savings
    
    # Merge routes based on savings
    used_vehicles = len(routes)
    for s, i, j in savings:
        if used_vehicles >= num_vehicles:
            break
        
        # Find routes containing i and j
        route_i = route_j = None
        for r in routes:
            if i in r:
                route_i = r
            if j in r:
                route_j = r
        
        if route_i is None or route_j is None or route_i == route_j:
            continue
        
        # Check if i and j are at route ends
        if not (route_i[0] == i or route_i[-1] == i) or not (route_j[0] == j or route_j[-1] == j):
            continue
        
        # Check capacity constraint
        load_i = sum(customer_demands[k-1] for k in route_i)
        load_j = sum(customer_demands[k-1] for k in route_j)
        if load_i + load_j > vehicle_capacity:
            continue
        
        # Merge routes
        if route_i[-1] == i and route_j[0] == j:
            new_route = route_i + route_j
        elif route_i[0] == i and route_j[-1] == j:
            new_route = route_j + route_i
        elif route_i[-1] == i and route_j[-1] == j:
            new_route = route_i + route_j[::-1]
        else:  # route_i[0] == i and route_j[0] == j
            new_route = route_j[::-1] + route_i
        
        # Update routes and loads
        routes.remove(route_i)
        routes.remove(route_j)
        routes.append(new_route)
        route_loads[routes.index(new_route)] = load_i + load_j
        used_vehicles = len(routes)
    
    return routes, dist_matrix, route_loads