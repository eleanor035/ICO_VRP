# Data cleaning and graph construction
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point

# Load combined GeoJSON file
gdf = gpd.read_file("data/processed/map.geojson")

# Split into roads (LineStrings) and taxi ranks (Points)
roads = gdf[gdf.geometry.type == 'LineString']
taxi_ranks = gdf[gdf.geometry.type == 'Point']