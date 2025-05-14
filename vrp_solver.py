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
    
    # Initialize routes: each customer in their own route
    routes = [[i + 1] for i in range(n_customers)]  # 1-based indexing for customers
    route_loads = [customer_demands[i] for i in range(n_customers)]
    
    # Calculate savings: s(i,j) = d(0,i) + d(0,j) - d(i,j)
    savings = []
    for i in range(1, n_customers + 1):
        for j in range(i + 1, n_customers + 1):
            s = dist_matrix[0, i] + dist_matrix[0, j] - dist_matrix[i, j]
            savings.append((s, i, j))
    
    # Sort by descending savings
    savings.sort(reverse=True)
    
    # Track which route each customer belongs to
    customer_route = {}
    for i in range(n_customers):
        customer_route[i + 1] = i  # Customer i+1 is in route i
    
    # Merge routes based on savings
    for s, i, j in savings:
        # Skip if savings are negative
        if s <= 0:
            continue
            
        # Find routes containing i and j
        route_i_idx = customer_route.get(i)
        route_j_idx = customer_route.get(j)
        
        # Skip if customers are already in the same route or not found
        if route_i_idx is None or route_j_idx is None or route_i_idx == route_j_idx:
            continue
            
        route_i = routes[route_i_idx]
        route_j = routes[route_j_idx]
        
        # Check if i and j are at the ends of their respective routes
        i_at_start = route_i[0] == i
        i_at_end = route_i[-1] == i
        j_at_start = route_j[0] == j
        j_at_end = route_j[-1] == j
        
        # Skip if neither customer is at an end of their route
        if not ((i_at_start or i_at_end) and (j_at_start or j_at_end)):
            continue
        
        # Check capacity constraint
        combined_load = route_loads[route_i_idx] + route_loads[route_j_idx]
        if combined_load > vehicle_capacity:
            continue
        
        # Merge routes properly based on positions
        new_route = []
        if i_at_end and j_at_start:
            new_route = route_i + route_j
        elif i_at_start and j_at_end:
            new_route = route_j + route_i
        elif i_at_end and j_at_end:
            new_route = route_i + list(reversed(route_j))
        elif i_at_start and j_at_start:
            new_route = list(reversed(route_i)) + route_j
        else:
            continue  # This shouldn't happen with our checks above
        
        # Update routes and loads
        routes[route_i_idx] = new_route
        route_loads[route_i_idx] = combined_load
        
        # Mark route_j as empty (we'll remove it later)
        routes[route_j_idx] = []
        route_loads[route_j_idx] = 0
        
        # Update customer_route mapping for all customers in the merged route
        for cust in new_route:
            customer_route[cust] = route_i_idx
    
    # Remove empty routes
    non_empty_routes = []
    non_empty_loads = []
    for i, route in enumerate(routes):
        if route:
            non_empty_routes.append(route)
            non_empty_loads.append(route_loads[i])
    
    # If we have more vehicles than required routes, it's fine
    # But if we have more routes than vehicles, we need to merge some
    while len(non_empty_routes) > num_vehicles:
        # Find the two smallest routes to merge
        min_load_idx1 = min_load_idx2 = -1
        min_load1 = min_load2 = float('inf')
        
        for i, load in enumerate(non_empty_loads):
            if load < min_load1:
                min_load2 = min_load1
                min_load_idx2 = min_load_idx1
                min_load1 = load
                min_load_idx1 = i
            elif load < min_load2:
                min_load2 = load
                min_load_idx2 = i
        
        # Merge these two routes if possible
        if min_load_idx1 >= 0 and min_load_idx2 >= 0:
            combined_load = non_empty_loads[min_load_idx1] + non_empty_loads[min_load_idx2]
            if combined_load <= vehicle_capacity:
                # Merge them
                non_empty_routes[min_load_idx1].extend(non_empty_routes[min_load_idx2])
                non_empty_loads[min_load_idx1] = combined_load
                
                # Remove the second route
                non_empty_routes.pop(min_load_idx2)
                non_empty_loads.pop(min_load_idx2)
            else:
                # If we can't merge the smallest routes, we can't reduce further
                break
        else:
            break
    
    return non_empty_routes, dist_matrix, non_empty_loads