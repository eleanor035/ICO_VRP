# src/preprocess_data.py
import logging
import geopandas as gpd
import networkx as nx
from shapely.ops import split, nearest_points
from pyproj import Transformer
from shapely.geometry import Point, LineString
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RoadNetworkProcessor:
    """Process raw geospatial data into routable network graph"""
    
    def __init__(self, raw_data_dir="data/raw", processed_data_dir="data/processed"):
        self.raw_data_dir = Path(raw_data_dir)
        self.processed_data_dir = Path(processed_data_dir)
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3763")
        self.G = nx.Graph()
        self.roads = None
        self.taxi_ranks = None

    def load_data(self):
        """Load and validate raw data"""
        try:
            # Load data from correct raw directory
            roads_path = self.processed_data_dir / "estradas_lisboa.geojson"
            taxi_ranks_path = self.processed_data_dir / "lisbon_taxi_ranks.geojson"
            
            self.roads = gpd.read_file(roads_path)
            self.taxi_ranks = gpd.read_file(taxi_ranks_path)
            
            # Validate and clean geometries
            self.roads = self.roads[self.roads.geometry.type == 'LineString']
            self.taxi_ranks = self.taxi_ranks[self.taxi_ranks.geometry.type == 'Point']
            self.roads = self.roads[~self.roads.is_empty]
            self.taxi_ranks = self.taxi_ranks[~self.taxi_ranks.is_empty]
            
            if self.roads.empty or self.taxi_ranks.empty:
                raise ValueError("Empty dataset loaded after filtering")
                
            logger.info(f"Loaded {len(self.roads)} roads and {len(self.taxi_ranks)} taxi ranks")
            
        except Exception as e:
            logger.error(f"Data loading failed: {str(e)}")
            raise

    def _reproject_data(self):
        """Convert data to UTM coordinates"""
        self.roads = self.roads.to_crs(epsg=3763)
        self.taxi_ranks = self.taxi_ranks.to_crs(epsg=3763)
        logger.debug("Reprojected data to UTM Zone 29N (EPSG:3763)")

    def _create_base_graph(self):
        """Build initial road network graph"""
        for idx, road in self.roads.iterrows():
            line = road.geometry
            if line.is_empty or not isinstance(line, LineString):
                continue
                
            coords = list(line.coords)
            for i in range(len(coords) - 1):
                self._add_edge(
                    start=coords[i],
                    end=coords[i+1],
                    length=line.length,
                    road_properties=road.drop('geometry').to_dict()
                )

        logger.info(f"Base graph created with {len(self.G.nodes)} nodes and {len(self.G.edges)} edges")

    def _add_edge(self, start, end, length, road_properties):
        """Add edge with attributes to graph"""
        start_id = self._node_id(start)
        end_id = self._node_id(end)
        
        # Convert LineString to WKT format
        edge_geometry = LineString([start, end]).wkt  # << Convert to WKT
        
        # Add nodes with default attributes if missing
        if start_id not in self.G.nodes:
            self.G.add_node(start_id, x=start[0], y=start[1], is_taxi_rank=False)
        if end_id not in self.G.nodes:
            self.G.add_node(end_id, x=end[0], y=end[1], is_taxi_rank=False)
        
        # Add edge with metadata
        self.G.add_edge(
            start_id, end_id,
            weight=length,
            geometry=edge_geometry,  # Now stores WKT string
            **road_properties
        )
    
    def _node_id(self, coords):
        """Generate precise node ID from coordinates (8 decimal places)"""
        return f"{coords[0]:.8f}_{coords[1]:.8f}"

    def _process_taxi_ranks(self):
        """Integrate taxi ranks into road network"""
        spatial_index = self.roads.sindex
        
        for idx, taxi in self.taxi_ranks.iterrows():
            # Get validated geometry object
            point = taxi.geometry
            
            # Validate geometry type and validity
            if not isinstance(point, Point) or not point.is_valid or point.is_empty:
                logger.warning(f"Skipping invalid taxi rank at index {idx}")
                continue
                
            # Find nearest road using spatial index (FIXED HERE)
            try:
                # Use the full Point geometry instead of bounds
                possible_matches = list(spatial_index.nearest(point))
                nearest_road_idx = possible_matches[0]
                road = self.roads.iloc[nearest_road_idx]
            except IndexError:
                logger.warning(f"No road found near taxi rank at {point}")
                continue

            # Split road and connect taxi node
            split_node_id = self._split_road_at_point(road, point)
            if split_node_id:
                self._add_taxi_node(split_node_id, taxi)

        logger.info(f"Processed {len(self.taxi_ranks)} taxi ranks")

    def _split_road_at_point(self, road, point):
        """Split road at point and return connection node ID"""
        # Extract scalar LineString from GeoSeries
        original_line = road.geometry.iloc[0]
        
        # Verify proximity to road
        distance = original_line.distance(point)
        if distance > 1.0:  # 1 meter tolerance
            logger.warning(f"Taxi rank too far from road ({distance:.2f}m)")
            return None

        # Find exact split point
        split_point = nearest_points(original_line, point)[0]
        split_node_id = self._node_id((split_point.x, split_point.y))
        
        try:
            # Split road geometry
            split_result = split(original_line, split_point)
            segments = [seg for seg in split_result.geoms if isinstance(seg, LineString)]
            
            if len(segments) != 2:
                logger.warning(f"Unexpected split result: {len(segments)} segments")
                return None

            # Remove original edges
            original_coords = list(original_line.coords)
            for i in range(len(original_coords) - 1):
                start_id = self._node_id(original_coords[i])
                end_id = self._node_id(original_coords[i+1])
                if self.G.has_edge(start_id, end_id):
                    self.G.remove_edge(start_id, end_id)

            # Add new split segments with connection to split point
            for seg in segments:
                seg_coords = list(seg.coords)
                for i in range(len(seg_coords) - 1):
                    self._add_edge(
                        seg_coords[i], seg_coords[i+1],
                        seg.length, road.drop('geometry').to_dict()
                    )
                
                # Connect to split point
                last_node = self._node_id(seg_coords[-1])
                self.G.add_edge(last_node, split_node_id, weight=0)
            
            return split_node_id

        except Exception as e:
            logger.error(f"Failed to split road: {str(e)}")
            return None

    def _add_taxi_node(self, node_id, taxi_data):
        """Mark existing node as taxi rank"""
        if node_id not in self.G.nodes:
            logger.warning(f"Taxi node {node_id} not found in graph")
            return
            
        # Update node attributes
        self.G.nodes[node_id].update({
            'is_taxi_rank': True,
            **taxi_data.drop('geometry').to_dict()
        })
        logger.debug(f"Added taxi rank at {node_id}")

    def save_results(self):
        """Save processed data to disk"""
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Save graph with XML writer
        nx.write_graphml(self.G, self.processed_data_dir / "road_network.graphml")  # Correct extension
        
        # Save reprojected roads
        self.roads.to_file(
            self.processed_data_dir / "roads_utm.geojson",
            driver="GeoJSON"
        )
        
        logger.info(f"Saved processed data to {self.processed_data_dir}")

    def process(self):
        """Main processing pipeline"""
        self.load_data()
        self._reproject_data()
        self._create_base_graph()
        self._process_taxi_ranks()
        self.save_results()
        return self.G

if __name__ == "__main__":
    processor = RoadNetworkProcessor()
    final_graph = processor.process()
    
    # Verify taxi integration
    taxi_nodes = [n for n, attr in final_graph.nodes(data=True) if attr.get('is_taxi_rank', False)]
    print(f"Successfully integrated {len(taxi_nodes)} taxi ranks into road network")