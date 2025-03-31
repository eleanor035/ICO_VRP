import networkx as nx
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer

class DynamicGraphManager:
    def __init__(self, base_graph_path, roads_path):
        self.G = nx.read_graphml(base_graph_path)
        self.roads = gpd.read_file(roads_path)
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3763")
        self.temp_nodes = {}
        
    def _find_nearest_edge(self, point_utm):
        """Find nearest edge using spatial index"""
        return self.roads.sindex.nearest(point_utm.bounds)[1][0]

    def add_depot(self, lat, lon):
        """Main interface for adding depots"""
        # Convert to UTM
        x, y = self.transformer.transform(lon, lat)
        depot_point = Point(x, y)
        
        # Check existing nodes within 10m
        existing_node = self._find_existing_node(depot_point)
        if existing_node:
            return existing_node
        
        # Find and split nearest edge
        edge_idx = self._find_nearest_edge(depot_point)
        new_graph, depot_node_id = self._split_edge(edge_idx, depot_point)
        
        self.temp_nodes[depot_node_id] = new_graph
        return depot_node_id

    def _find_existing_node(self, point):
        """Check for existing nodes within tolerance"""
        for node in self.G.nodes:
            node_point = Point(self.G.nodes[node]['x'], self.G.nodes[node]['y'])
            if node_point.distance(point) < 10:  # 10m tolerance
                return node
        return None

    def _split_edge(self, edge_idx, point):
        """Split edge and create temporary subgraph"""
        # Implementation similar to previous add_temporary_depot
        # Returns modified subgraph and depot node ID