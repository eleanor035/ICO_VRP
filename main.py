# main.py
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

import networkx as nx
from flask import Flask, request, jsonify, send_from_directory, g
from pyproj import Transformer
from pyproj.exceptions import CRSError
from graph_manager import DynamicGraphManager
from visualization import visualize_graph
from vrp_solver import solve_vrp

# Configure paths
BASE_DIR = Path(__file__).parent
BASE_GRAPH_PATH = BASE_DIR / "data/processed/road_network.graphml"
ROADS_UTM_PATH = BASE_DIR / "data/processed/roads_utm.geojson"

app = Flask(__name__,
           static_folder=str(BASE_DIR / "web/static"),
           template_folder=str(BASE_DIR / "web/templates"))

def initialize_services():
    """Initialize core components with thread-safe approach"""
    if 'graph_manager' not in g:
        g.graph_manager = DynamicGraphManager(BASE_GRAPH_PATH, ROADS_UTM_PATH)
        
    # Initialize transformer once per application
    if not hasattr(app, 'transformer'):
        app.transformer = Transformer.from_crs("EPSG:3763", "EPSG:4326")

def setup_application():
    """Run initial data processing if needed"""
    # Create required directories
    os.makedirs(BASE_DIR / "data/processed", exist_ok=True)
    os.makedirs(BASE_DIR / "web/static/routes", exist_ok=True)

    # Process data if missing
    if not all([BASE_GRAPH_PATH.exists(), ROADS_UTM_PATH.exists()]):
        print("Running initial data processing...")
        from src.preprocess_data import RoadNetworkProcessor
        RoadNetworkProcessor().process()

# Run setup when app starts
with app.app_context():
    setup_application()

# Serve main interface from root URL
@app.route("/")
def home():
    return send_from_directory("web/templates", "vrp_interface.html")

# Optional: Explicit route for /web/vrp_interface.html
@app.route("/web/vrp_interface.html")
def serve_vrp_interface():
    return send_from_directory("web/templates", "vrp_interface.html")

@app.route('/set_depot', methods=['GET'])
def handle_depot():
    """Handle depot placement and return optimized routes"""
    try:
        initialize_services()
        
        # Validate coordinates
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lng', type=float)
        if None in (lat, lon):
            return jsonify({"status": "error", "message": "Missing coordinates"}), 400

        # Add depot to graph
        G_temp, depot_id = g.graph_manager.add_depot(lat, lon)
        
        # Solve VRP and transform coordinates
        routes = solve_vrp(G_temp, depot_id)
        transformed_routes = transform_route_coordinates(G_temp, routes)

        return jsonify({
            "status": "success",
            "routes": transformed_routes,
            "depot": {"lat": lat, "lon": lon}
        })

    except (ValueError, CRSError) as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Depot error: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

# Improved /solve-vrp endpoint
@app.route('/solve-vrp', methods=['POST'])
def solve_vrp_endpoint():
    try:
        initialize_services()  # Initialize graph_manager
        data = request.get_json()
        depot = data['depot']
        
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3763")
        x, y = transformer.transform(depot['lng'], depot['lat'])
        
        G_temp, depot_id = g.graph_manager.add_depot(x, y)
        
        routes = solve_vrp(G_temp, depot_id)
        return jsonify({
            "status": "success",
            "routes": transform_route_coordinates(G_temp, routes)
        })

    except Exception as e:
        app.logger.error(f"VRP Error: {str(e)}")
        return jsonify({"status": "error", "message": "VRP solution failed"}), 500

@app.route('/visualize')
def visualize_routes():
    """Generate visualization image"""
    try:
        initialize_services()
        img_path = visualize_graph(g.graph_manager.G)
        return send_from_directory(BASE_DIR / "web/static/routes", img_path)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

def transform_route_coordinates(graph, routes):
    """Transform route coordinates from UTM to WGS84"""
    transformed = []
    for route in routes:
        geo_route = []
        for node in route:
            x = graph.nodes[node]['x']
            y = graph.nodes[node]['y']
            lon, lat = app.transformer.transform(x, y)
            geo_route.append((lat, lon))
        transformed.append(geo_route)
    return transformed

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)