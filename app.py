import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import random
import math
from vrp_solver import clarke_wright
from map_visualization import create_map

# Set page configuration
st.set_page_config(
    page_title="Vehicle Routing Problem Solver",
    page_icon="✈️",
    layout="wide"
)

# App title and description
st.title("Vehicle Routing Problem Solver")
st.markdown("""
This application solves the Capacitated Vehicle Routing Problem (CVRP) using the Clarke-Wright savings algorithm.
Customer locations and demands are randomly generated within a specified radius around the depot.
""")

# Function to generate random customer locations within a radius
def generate_random_customers_in_radius(depot_lat, depot_lon, radius_km, num_customers, max_demand):
    """Generates random customer locations and demands within a given radius of the depot."""
    customer_coords = []
    customer_demands = []
    R = 6371  # Earth radius in km
    
    for _ in range(num_customers):
        # Generate random distance and angle
        rand_dist = radius_km * math.sqrt(random.random())
        rand_angle = 2 * math.pi * random.random()
        
        # Convert depot lat/lon to radians
        lat1 = math.radians(depot_lat)
        lon1 = math.radians(depot_lon)
        
        # Calculate new point coordinates
        angular_distance = rand_dist / R
        
        lat2 = math.asin(math.sin(lat1) * math.cos(angular_distance) +
                         math.cos(lat1) * math.sin(angular_distance) * math.cos(rand_angle))
        
        lon2 = lon1 + math.atan2(math.sin(rand_angle) * math.sin(angular_distance) * math.cos(lat1),
                                 math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2))
        
        # Convert back to degrees
        customer_coords.append((math.degrees(lat2), math.degrees(lon2)))
        # Generate random demand
        customer_demands.append(random.randint(1, max_demand))
        
    return customer_coords, customer_demands

# Sidebar for inputs
with st.sidebar:
    # Depot location
    st.subheader("Depot Location")
    depot_lat = st.number_input("Depot Latitude", value=6.8209, format="%.4f")
    depot_lon = st.number_input("Depot Longitude", value=80.0397, format="%.4f")

    # Number of customers
    st.subheader("Customers")
    num_customers = st.slider("Number of Customers", min_value=3, max_value=50, value=10)
    
    # Generation Radius
    st.subheader("Generation Radius")
    radius_km = st.slider("Radius around Depot (km)", min_value=5.0, max_value=100.0, value=25.0, step=1.0)
    
    # Customer demands
    st.subheader("Customer Demands")
    max_demand = st.slider("Maximum Customer Demand", min_value=1, max_value=50, value=10)
    
    # Vehicle capacity
    st.subheader("Vehicles")
    vehicle_capacity = st.slider("Vehicle Capacity", min_value=10, max_value=200, value=50)
    num_vehicles = st.slider("Number of Vehicles", min_value=1, max_value=10, value=3)
    
    # Solve button
    solve_button = st.button("Solve VRP", type="primary")

# Main content area
if solve_button:
    with st.spinner("Solving VRP..."):
        depot_coords = (depot_lat, depot_lon)
        
        # Generate customer coordinates and demands
        customer_coords, customer_demands = generate_random_customers_in_radius(
            depot_lat, depot_lon, radius_km, num_customers, max_demand
        )
        
        # Display generated customer locations and demands
        st.subheader("Generated Customer Locations and Demands")
        customer_data = {
            'Customer ID': list(range(1, num_customers + 1)),
            'Latitude': [coord[0] for coord in customer_coords],
            'Longitude': [coord[1] for coord in customer_coords],
            'Demand': customer_demands
        }
        st.dataframe(pd.DataFrame(customer_data), use_container_width=True)
        
        # Solve VRP
        routes, dist_matrix, route_loads = clarke_wright(
            depot_coords, customer_coords, customer_demands, vehicle_capacity, num_vehicles
        )
        
        # Create map visualization
        vrp_map = create_map(depot_coords, customer_coords, routes)
        
        # Display results
        st.subheader("Solution")
        
        # Display routes
        st.write("### Routes")
        total_distance = 0
        
        if not routes:
            st.write("No routes generated. Check parameters.")
        else:
            for i, route in enumerate(routes):
                if not route:
                    continue
                    
                # Calculate route distance
                route_dist = dist_matrix[0, route[0]]  # Depot to first customer
                for k in range(len(route) - 1):
                    route_dist += dist_matrix[route[k], route[k+1]]
                route_dist += dist_matrix[route[-1], 0]  # Last customer to Depot
                total_distance += route_dist
                
                # Display route details
                st.write(f"**Route {i+1}:** Depot → {' → '.join([f'Customer {j}' for j in route])} → Depot")
                st.write(f"Distance: {route_dist:.2f} km")
                st.write(f"Load: {route_loads[i]:.2f} / {vehicle_capacity:.2f} units")
            
            st.write(f"**Total Distance:** {total_distance:.2f} km")
        
        # Display map
        st.subheader("Route Visualization")
        st.markdown(
            "<span style='color:red'>Hold the cursor over the route to see its name, because the random color generator sometimes produces similar colors.</span>",
            unsafe_allow_html=True
        )
        folium_static(vrp_map, width=1000)