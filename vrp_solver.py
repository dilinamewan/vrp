import numpy as np

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the earth."""
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def calculate_savings(depot_coords, customer_coords):
    """Calculate savings for merging routes for all customer pairs."""
    num_customers = len(customer_coords)
    savings = []
    # Calculate distance matrix including depot (index 0)
    all_coords = [depot_coords] + customer_coords
    dist_matrix = np.zeros((num_customers + 1, num_customers + 1))
    for i in range(num_customers + 1):
        for j in range(i, num_customers + 1):
            dist = haversine(all_coords[i][0], all_coords[i][1], all_coords[j][0], all_coords[j][1])
            dist_matrix[i, j] = dist
            dist_matrix[j, i] = dist

    # Calculate savings S(i, j) = d(depot, i) + d(depot, j) - d(i, j)
    for i in range(1, num_customers + 1):
        for j in range(i + 1, num_customers + 1):
            saving = dist_matrix[0, i] + dist_matrix[0, j] - dist_matrix[i, j]
            savings.append(((i, j), saving))

    # Sort savings in descending order
    savings.sort(key=lambda x: x[1], reverse=True)
    return savings, dist_matrix

def clarke_wright(depot_coords, customer_coords, customer_demands, vehicle_capacity, num_vehicles=None):
    """Solves the VRP using the Clarke-Wright savings algorithm with capacity constraints.

    Args:
        depot_coords (tuple): (latitude, longitude) of the depot.
        customer_coords (list): List of (latitude, longitude) tuples for customers.
        customer_demands (list): List of demand values for each customer.
        vehicle_capacity (float): Maximum capacity per vehicle.
        num_vehicles (int, optional): Maximum number of routes (vehicles). Defaults to None (unlimited).

    Returns:
        list: A list of routes, where each route is a list of customer indices (starting from 1).
        numpy.ndarray: The distance matrix.
        list: Current load for each route.
    """
    num_customers = len(customer_coords)
    if num_customers == 0:
        return [], np.zeros((1, 1)), []

    savings, dist_matrix = calculate_savings(depot_coords, customer_coords)

    # Initial routes: Depot -> Customer i -> Depot for all i
    routes = [[i] for i in range(1, num_customers + 1)]
    # Track route loads
    route_loads = customer_demands.copy()

    # Route Merging
    for (i, j), saving in savings:
        # Find routes containing customers i and j
        route_i_idx, route_j_idx = -1, -1
        for idx, route in enumerate(routes):
            if i in route:
                route_i_idx = idx
            if j in route:
                route_j_idx = idx
            if route_i_idx != -1 and route_j_idx != -1:
                break

        # Check if i and j are in different routes
        if route_i_idx != route_j_idx:
            route_i = routes[route_i_idx]
            route_j = routes[route_j_idx]

            # Check capacity constraint
            new_load = route_loads[route_i_idx] + route_loads[route_j_idx]
            if new_load > vehicle_capacity:
                continue

            # Check merge conditions
            can_merge_ij = (route_i[-1] == i and route_j[0] == j)
            can_merge_ji = (route_j[-1] == j and route_i[0] == i)

            merged = False
            if can_merge_ij:
                new_route = route_i + route_j
                routes[route_i_idx] = new_route
                routes.pop(route_j_idx)
                route_loads[route_i_idx] = new_load
                route_loads.pop(route_j_idx)
                merged = True
            elif can_merge_ji:
                new_route = route_j + route_i
                if route_i_idx > route_j_idx:
                    routes[route_j_idx] = new_route
                    routes.pop(route_i_idx)
                    route_loads[route_j_idx] = new_load
                    route_loads.pop(route_i_idx)
                else:
                    routes[route_i_idx] = new_route
                    routes.pop(route_j_idx)
                    route_loads[route_i_idx] = new_load
                    route_loads.pop(route_j_idx)
                merged = True

            # Check vehicle limit
            if merged and num_vehicles is not None and len(routes) == num_vehicles:
                break

    return routes, dist_matrix, route_loads