import folium
import random

def generate_random_color():
    """Generates a random hex color code."""
    return '#{:06x}'.format(random.randint(0, 0xFFFFFF))

def create_map(depot_coords, customer_coords, routes):
    """Creates a Folium map visualizing the VRP solution with a dark theme."""
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
        
    # Draw Routes
    for i, route in enumerate(routes):
        if not route:
            continue
        
        route_color = generate_random_color()
        
        route_points = [depot_coords]
        for customer_index in route:
            route_points.append(customer_coords[customer_index - 1])
        route_points.append(depot_coords)

        folium.PolyLine(
            locations=route_points,
            color=route_color,
            weight=3,
            opacity=0.8,
            tooltip=f"Route {i+1}"
        ).add_to(m)

    return m