import os
import folium
import networkx as nx
from pyproj import Transformer

def visualize_graph():
    """Visualize the preprocessed graph"""
    # Create output directory
    if not os.path.exists("web"):
        os.makedirs("web")
    
    # Load graph
    G = nx.read_graphml("data/processed/road_network.graphml")
    
    # Coordinate transformer
    transformer = Transformer.from_crs("EPSG:3763", "EPSG:4326", always_xy=True)
    
    # Create map
    m = folium.Map(location=[38.7223, -9.1393], zoom_start=13, tiles="OpenStreetMap")
    
    # Add roads
    for edge in G.edges:
        start = G.nodes[edge[0]]
        end = G.nodes[edge[1]]
        lon_start, lat_start = transformer.transform(start['x'], start['y'])
        lon_end, lat_end = transformer.transform(end['x'], end['y'])
        folium.PolyLine(
            locations=[[lat_start, lon_start], [lat_end, lon_end]],
            color='grey', weight=1.5
        ).add_to(m)
    
    # Add taxi ranks
    taxi_nodes = [n for n in G.nodes if G.nodes[n].get('is_taxi_rank', False)]
    for node in taxi_nodes:
        lon, lat = transformer.transform(G.nodes[node]['x'], G.nodes[node]['y'])
        folium.CircleMarker(
            location=[lat, lon], radius=5, color='red', popup=f"Taxi Rank: {node}"
        ).add_to(m)
    
    # Save map
    m.save("web/vrp_graph_map.html")
    print("Map saved to web/vrp_graph_map.html")

if __name__ == "__main__":
    visualize_graph()