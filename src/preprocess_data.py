# Data cleaning and graph construction
import geopandas as gpd
import networkx as nx
from shapely.ops import split, nearest_points

def split_line_at_point(line, point):
    """Split a LineString at a point with validation"""
    if line.distance(point) > 0.1:  # 10cm tolerance
        return [line]
    split_result = split(line, line.interpolate(line.project(point)))
    return list(split_result.geoms) if split_result.geom_type == 'GeometryCollection' else [split_result]

# Load data
gdf = gpd.read_file("data/processed/map.geojson")
roads = gdf[gdf.geometry.type == 'LineString'].copy()
taxi_ranks = gdf[gdf.geometry.type == 'Point'].copy()

# Reproject to UTM Zone 29N (EPSG:3763)
roads = roads.to_crs(epsg=3763)
taxi_ranks = taxi_ranks.to_crs(epsg=3763)

G = nx.Graph()

# Add roads with string IDs and attributes
for _, road in roads.iterrows():
    coords = list(road.geometry.coords)
    for i in range(len(coords) - 1):
        start = coords[i]
        end = coords[i+1]
        start_id = f"{start[0]}_{start[1]}"
        end_id = f"{end[0]}_{end[1]}"
        
        G.add_node(start_id, x=start[0], y=start[1], is_taxi_rank=False)
        G.add_node(end_id, x=end[0], y=end[1], is_taxi_rank=False)
        G.add_edge(start_id, end_id, weight=road.geometry.length)

# Process taxi ranks
for _, taxi in taxi_ranks.iterrows():
    point = taxi.geometry
    closest_road = roads.distance(point).idxmin()
    road_geom = roads.loc[closest_road].geometry
    
    # Split road
    split_result = split_line_at_point(road_geom, point)
    
    # Remove original edges
    original_coords = list(road_geom.coords)
    for i in range(len(original_coords) - 1):
        start = f"{original_coords[i][0]}_{original_coords[i][1]}"
        end = f"{original_coords[i+1][0]}_{original_coords[i+1][1]}"
        if G.has_edge(start, end):
            G.remove_edge(start, end)
    
    # Add new split segments
    for new_line in split_result:
        new_coords = list(new_line.coords)
        for i in range(len(new_coords) - 1):
            start = f"{new_coords[i][0]}_{new_coords[i][1]}"
            end = f"{new_coords[i+1][0]}_{new_coords[i+1][1]}"
            G.add_node(start, x=new_coords[i][0], y=new_coords[i][1], is_taxi_rank=False)
            G.add_node(end, x=new_coords[i+1][0], y=new_coords[i+1][1], is_taxi_rank=False)
            G.add_edge(start, end, weight=new_line.length)
    
    # Add taxi rank node with coordinates
    snapped_point = nearest_points(road_geom, point)[0]
    node_id = f"{snapped_point.x}_{snapped_point.y}"
    G.add_node(node_id, x=snapped_point.x, y=snapped_point.y, is_taxi_rank=True)  # Fixed!

# Save graph
nx.write_graphml(G, "data/processed/road_network.graphml")
print("Graph saved with", len(G.nodes), "nodes and", len(G.edges), "edges.")