# Data cleaning and graph construction
import geopandas as gpd
import networkx as nx
from shapely.ops import split, nearest_points

gdf = gpd.read_file("data/processed/map.geojson")
roads = gdf[gdf.geometry.type == 'LineString'].copy()
taxi_ranks = gdf[gdf.geometry.type == 'Point'].copy()

roads = roads.to_crs(epsg=3763)
taxi_ranks = taxi_ranks.to_crs(epsg=3763) #Portugal UTM zone

G = nx.Graph()

def split_line_at_point(line, point):
    """Safely split a LineString at a point, returns list of LineStrings"""
    if line.distance(point) > 0.1:  
        return [line]  
    split_result = split(line, line.interpolate(line.project(point)))
    return list(split_result.geoms)  

for _, road in roads.iterrows():
    coords = list(road.geometry.coords)
    for i in range(len(coords) - 1):
        start = coords[i]
        end = coords[i+1]
        G.add_edge(start, end, weight=road.geometry.length)

for _, taxi in taxi_ranks.iterrows():
    point = taxi.geometry
    closest_road = roads.distance(point).idxmin()
    road_geom = roads.loc[closest_road].geometry
    
    split_result = split_line_at_point(road_geom, point)
    
    original_coords = list(road_geom.coords)
    for i in range(len(original_coords) - 1):
        G.remove_edge(original_coords[i], original_coords[i+1])
    
    for new_line in split_result: 
        new_coords = list(new_line.coords) 
        for i in range(len(new_coords) - 1):
            start = new_coords[i]
            end = new_coords[i+1]
            G.add_edge(start, end, weight=new_line.length)
    
    snapped_point = nearest_points(road_geom, point)[0]
    G.add_node(snapped_point.coords[0], is_taxi_rank=True)

sample_road = roads.iloc[0].geometry
sample_point = taxi_ranks.iloc[0].geometry
split_test = split_line_at_point(sample_road, sample_point)
print("Split result type:", type(split_test[0]))  # Should be <class 'shapely.LineString'>

nx.write_graphml(G, "data/processed/road_network.graphml")
