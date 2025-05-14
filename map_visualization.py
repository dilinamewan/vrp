import folium
import random
import requests
import streamlit as st

def generate_random_color():
    """Generates a random hex color code."""
    return '#{:06x}'.format(random.randint(0, 0xFFFFFF))

def get_osrm_route(start_coord, end_coord, retry=False):
    """Fetches road-based route coordinates from OSRM API between two points."""
    # Validate coordinates
    if not (-90 <= start_coord[0] <= 90 and -180 <= start_coord[1] <= 180 and
            -90 <= end_coord[0] <= 90 and -180 <= end_coord[1] <= 180):
        st.warning(f"Invalid coordinates: {start_coord} to {end_coord}")
        print(f"Invalid coordinates: {start_coord} to {end_coord}")
        return None

    # OSRM public API endpoint
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=full&geometries=geojson"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("routes"):
            # Extract route geometry (list of coordinates)
            route_coords = [(point[1], point[0]) for point in data["routes"][0]["geometry"]["coordinates"]]
            print(f"OSRM success for {start_coord} to {end_coord}: {len(route_coords)} points")
            return route_coords
        else:
            print(f"OSRM no route found for {start_coord} to {end_coord}: {data.get('message', 'No message')}")
            # Retry with slight offset if requested
            if not retry:
                offset_start = (start_coord[0] + 0.0001, start_coord[1] + 0.0001)
                offset_end = (end_coord[0] + 0.0001, end_coord[1] + 0.0001)
                print(f"Retrying with offset: {offset_start} to {offset_end}")
                return get_osrm_route(offset_start, offset_end, retry=True)
            st.warning(f"No route found for {start_coord} to {end_coord}")
            return None
    except requests.RequestException as e:
        print(f"OSRM API error for {start_coord} to {end_coord}: {e}")
        # Retry with slight offset if requested
        if not retry:
            offset_start = (start_coord[0] + 0.0001, start_coord[1] + 0.0001)
            offset_end = (end_coord[0] + 0.0001, end_coord[1] + 0.0001)
            print(f"Retrying with offset: {offset_start} to {offset_end}")
            return get_osrm_route(offset_start, offset_end, retry=True)
        st.warning(f"OSRM API failed for {start_coord} to {end_coord}: {e}")
        return None

def create_map(depot_coords, customer_coords, routes):
    """Creates a Folium map visualizing the VRP solution with road-based routes."""
    # Calculate map center
    all_lats = [depot_coords[0]] + [c[0] for c in customer_coords]
    all_lons = [depot_coords[1]] + [c[1] for c in customer_coords]
    map_center = [sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons)]

    # Create base map with dark theme
    m = folium.Map(location=map_center, zoom_start=10, tiles='CartoDB dark_matter')

    # Add Depot Marker
    folium.Marker(
        location=depot_coords,
        popup="Depot",
        tooltip="Depot",
        icon=folium.Icon(color='red', icon='industry', prefix='fa') 
    ).add_to(m)

    # Add Customer Markers
    for i, coords in enumerate(customer_coords):
        folium.Marker(
            location=coords,
            popup=f"Customer {i+1}",
            tooltip=f"Customer {i+1}",
            icon=folium.Icon(color='blue', icon='user', prefix='fa')
        ).add_to(m)
        
    # Draw Routes using OSRM
    for i, route in enumerate(routes):
        if not route:
            continue
        
        route_color = generate_random_color()
        route_points = []
        
        # Start from depot
        route_points.append(depot_coords)
        for customer_index in route:
            route_points.append(customer_coords[customer_index - 1])
        route_points.append(depot_coords)

        # Draw road-based route segments
        for j in range(len(route_points) - 1):
            start = route_points[j]
            end = route_points[j + 1]
            road_coords = get_osrm_route(start, end)
            if road_coords:
                folium.PolyLine(
                    locations=road_coords,
                    color=route_color,
                    weight=3,
                    opacity=0.8,
                    tooltip=f"Route {i+1}"
                ).add_to(m)
            else:
                # Fallback to straight line with warning
                folium.PolyLine(
                    locations=[start, end],
                    color=route_color,
                    weight=3,
                    opacity=0.8,
                    tooltip=f"Route {i+1} (fallback - no road route)"
                ).add_to(m)

    return m