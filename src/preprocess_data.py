# Data cleaning and graph construction
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point

gdf = gpd.read_file("data/processed/map.geojson")

roads = gdf[gdf.geometry.type == 'LineString']
taxi_ranks = gdf[gdf.geometry.type == 'Point']