import geopandas as gpd
import networkx as nx
import osmnx as ox
import folium
from shapely.geometry import LineString, Point
import random
import numpy as np
import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from geopy.distance import geodesic

#Mapbox API access token
access_token = "pk.eyJ1IjoibGVvbm9ycGlzY28iLCJhIjoiY205MDk3emFyMGkxZDJqc2F3Y2NzZjRjaSJ9.4m1DGg4-A5kxZLCJTmA6iQ"

start_lon, start_lat = -9.139337, 38.736946  
end_lon, end_lat = -9.152, 38.720             

# Construct the URL for the Directions API with traffic information
url = (
    f"https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
    f"{start_lon},{start_lat};{end_lon},{end_lat}"
    f"?access_token={access_token}&geometries=geojson"
)
# Make the request to the Mapbox Directions API
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    travel_time_seconds = data['routes'][0]['duration']
    travel_time_minutes = travel_time_seconds / 60

    print(f"Mapbox: Travel time including traffic: {travel_time_seconds} seconds (~{travel_time_minutes:.1f} minutes)")
else:
    print("Error querying Mapbox API:", response.text)

estradas = gpd.read_file('data/processed/estradas_lisboa.geojson')
taxi_ranks = gpd.read_file('data/processed/lisbon_taxi_ranks.geojson')

G = nx.Graph()
G.graph["crs"] = "EPSG:4326"
node_mapping = {}

for _, row in estradas.iterrows():
    if isinstance(row.geometry, LineString):
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            u_coord, v_coord = coords[i], coords[i + 1]
            if u_coord not in node_mapping:
                node_mapping[u_coord] = len(node_mapping)
                G.add_node(node_mapping[u_coord], x=u_coord[0], y=u_coord[1])
            if v_coord not in node_mapping:
                node_mapping[v_coord] = len(node_mapping)
                G.add_node(node_mapping[v_coord], x=v_coord[0], y=v_coord[1])
            u, v = node_mapping[u_coord], node_mapping[v_coord]
            distance = ox.distance.great_circle(u_coord[1], u_coord[0],
                                                v_coord[1], v_coord[0])
            G.add_edge(u, v, weight=distance)

if not nx.is_connected(G):
    largest_cc = max(nx.connected_components(G), key=len)
    G = G.subgraph(largest_cc).copy()

num_clients = 4
client_points = []
for _ in range(num_clients):
    random_row = estradas.sample(1).iloc[0]
    if isinstance(random_row.geometry, LineString):
        mid_coord = random_row.geometry.interpolate(0.5, normalized=True).coords[0]
        client_points.append(Point(mid_coord))

depots = [Point(row.geometry.x, row.geometry.y) for _, row in taxi_ranks.iterrows()]
def total_distance(depot):
    return sum(depot.distance(client) for client in client_points)
nearest_depot = min(depots, key=total_distance)

stops = [nearest_depot] + client_points
n_stops = len(stops)


def compute_distance(p1, p2):
    # Calculate the distance in meters
    distance_meters = geodesic((p1.y, p1.x), (p2.y, p2.x)).meters
    
    if distance_meters < 1000:
        return distance_meters 
    else:
        return distance_meters / 1000 


distance_matrix = np.zeros((n_stops, n_stops))
for i in range(n_stops):
    for j in range(n_stops):
        distance_matrix[i][j] = compute_distance(stops[i], stops[j]) if i != j else 0

data = {}
data['distance_matrix'] = distance_matrix.tolist()
data['demands'] = [0] + [1] * (n_stops - 1) 
data['vehicle_capacities'] = [4]
data['num_vehicles'] = 1
data['depot'] = 0

manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                       data['num_vehicles'], data['depot'])

routing = pywrapcp.RoutingModel(manager)

# Define cost of each arc.
def distance_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    # Multiply by 1000 to convert to integer values
    return int(data['distance_matrix'][from_node][to_node] * 1000)

transit_callback_index = routing.RegisterTransitCallback(distance_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

def demand_callback(from_index):
    from_node = manager.IndexToNode(from_index)
    return data['demands'][from_node]

demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0, 
    data['vehicle_capacities'],  
    True,  
    'Capacity')

search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

solution = routing.SolveWithParameters(search_parameters)
if solution:
    index = routing.Start(0)
    route_order = []
    while not routing.IsEnd(index):
        node_index = manager.IndexToNode(index)
        route_order.append(node_index)
        index = solution.Value(routing.NextVar(index))
    route_order.append(manager.IndexToNode(index))
else:
    raise Exception("No solution found!")

print("VRP route order (indices in stops):", route_order)

m = folium.Map(location=[nearest_depot.y, nearest_depot.x],
               zoom_start=14, tiles="cartodbpositron")

route_coords = []
for i in range(len(route_order) - 1):
    origin = stops[route_order[i]]
    destination = stops[route_order[i+1]]
    
    origin_node = ox.distance.nearest_nodes(G, origin.x, origin.y)
    destination_node = ox.distance.nearest_nodes(G, destination.x, destination.y)
    
    sp = nx.shortest_path(G, source=origin_node, target=destination_node, weight="weight")
    sp_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in sp]
    route_coords.extend(sp_coords)
    
    if i > 0 and i < len(route_order) - 1:
        folium.Marker(
            [origin.y, origin.x],
            popup=f"Paragem {i}",
            icon=folium.DivIcon(
                icon_size=(30, 30),
                icon_anchor=(10, 10),
                html=f'<div style="font-size: 12pt; color: white; background-color: green; padding: 4px; border-radius: 50%; display: flex; justify-content: center">{i}</div>'

        )).add_to(m)

start_stop = stops[route_order[0]]
end_stop = stops[route_order[-1]]
midpoint = route_coords[len(route_coords)//2]

if route_order[0] == route_order[-1]:
    folium.Marker(
        [start_stop.y, start_stop.x],
        popup="Início/Fim: Praça de Táxis",
        icon=folium.Icon(color="darkred", icon="play", prefix='fa')
    ).add_to(m)
else:
    folium.Marker(
        [start_stop.y, start_stop.x],
        popup="Início: Praça de Táxis",
        icon=folium.Icon(color="darkred", icon="play", prefix='fa')
    ).add_to(m)
    folium.Marker(
        [end_stop.y, end_stop.x],
        popup=("Fim: Praça de Táxis" if route_order[-1] == 0 
               else f"End: Paragem {len(route_order)-1}"),
        icon=folium.Icon(color="darkred", icon="stop", prefix='fa')
    ).add_to(m)

distance_km = compute_distance(stops[route_order[0]], stops[route_order[-1]])

info_text = (
    f"<b>Tempo Esperado de Viagem: {travel_time_minutes:.1f} min</b><br>"
    f"<b>Distância: {distance:.2f} </b>"
)

folium.Marker(
    location=midpoint,
    popup=f"Tempo Esperado de Viagem: {travel_time_minutes:.1f} minutes",
    icon=folium.Icon(color="blue", icon="clock", prefix='fa')
).add_to(m)

folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)

map_path = "web/templates/mapa_final.html"
m.save(map_path)
print("Map saved to:", map_path)