import networkx as nx
import folium
from shapely.geometry import Point

def visualize_graph():
    # Load the graph
    G = nx.read_graphml("data/processed/road_network.graphml")

    # Convert node coordinates to numeric types (NetworkX may read them as strings)
    for node in G.nodes:
        G.nodes[node]['x'] = float(G.nodes[node]['x'])
        G.nodes[node]['y'] = float(G.nodes[node]['y'])

    # Create a Folium map centered on Lisbon
    lisbon_center = [38.7223, -9.1393]
    m = folium.Map(location=lisbon_center, zoom_start=13, tiles="OpenStreetMap")

    # Add road edges to the map
    for edge in G.edges:
        start = G.nodes[edge[0]]
        end = G.nodes[edge[1]]
        folium.PolyLine(
            locations=[
                [start['y'], start['x']],  # Folium uses [lat, lon]
                [end['y'], end['x']]
            ],
            color='gray',
            weight=1,
            opacity=0.7
        ).add_to(m)

    # Add taxi rank nodes (marked with is_taxi_rank=True)
    taxi_nodes = [node for node in G.nodes if G.nodes[node].get('is_taxi_rank', False)]
    for node in taxi_nodes:
        folium.CircleMarker(
            location=[G.nodes[node]['y'], G.nodes[node]['x']],
            radius=5,
            color='red',
            fill=True,
            fill_color='red',
            popup=f"Taxi Rank: {node}"
        ).add_to(m)

    # Save the map
    m.save("../web/vrp_graph_map.html")
    print("Map saved to web/vrp_graph_map.html")

if __name__ == "__main__":
    visualize_graph()