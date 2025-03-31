# main.py
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import networkx as nx
from flask import Flask, request, jsonify, send_from_directory, g
from pyproj import Transformer
from pyproj.exceptions import CRSError
from graph_manager import DynamicGraphManager
from visualization import visualize_graph
from vrp_solver import solve_vrp
from map_interface import VRPMapInterface


app = Flask(__name__)

# Initialize core components
BASE_GRAPH_PATH = "data/processed/road_network.graphml"
ROADS_UTM_PATH = "data/processed/roads_utm.geojson"

# Ensure processed data exists
if not all(os.path.exists(p) for p in [BASE_GRAPH_PATH, ROADS_UTM_PATH]):
    print("Running initial data processing...")
    from preprocess_data import G as base_graph
    from preprocess_data import roads  # Import UTM roads
    
    # Save processed data to disk
    nx.write_graphml(base_graph, BASE_GRAPH_PATH)
    roads.to_file(ROADS_UTM_PATH, driver="GeoJSON")

# Initialize services
graph_manager = DynamicGraphManager(BASE_GRAPH_PATH, ROADS_UTM_PATH)
map_interface = VRPMapInterface()

@app.route("/web/vrp_interface.html")
def serve_vrp_interface():
    return send_from_directory("web", "vrp_interface.html")

@app.route("/")
def home():
    return send_from_directory("web", "vrp_interface.html")

@app.route('/set_depot', methods=['GET'])
def handle_depot():
    """Handle depot placement and return optimized routes"""
    try:
        # Validate input
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lng', type=float)
        if lat is None or lon is None:
            return jsonify({"status": "error", "message": "Missing lat/lon parameters"}), 400
        
        # Initialize graph manager (thread-safe)
        if 'graph_manager' not in g:
            g.graph_manager = DynamicGraphManager()
        
        # Add depot to graph
        G_temp, depot_id = g.graph_manager.add_depot(lat, lon)
        
        # Solve VRP
        routes = solve_vrp(G_temp, depot_id, edge_coverage=True)
        
        # Transform coordinates
        transformer = Transformer.from_crs("EPSG:3763", "EPSG:4326")
        transformed_routes = []
        for route in routes:
            geo_route = []
            for node in route:
                x = G_temp.nodes[node]['x']
                y = G_temp.nodes[node]['y']
                try:
                    lon_geo, lat_geo = transformer.transform(x, y)
                    geo_route.append((lat_geo, lon_geo))
                except CRSError as e:
                    raise ValueError(f"Coordinate transformation failed: {e}")
            transformed_routes.append(geo_route)
        
        # Return routes to frontend (let JS draw them)
        return jsonify({
            "status": "success",
            "routes": transformed_routes,
            "depot": {"lat": lat, "lon": lon}
        })
    
    except (ValueError, CRSError) as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Internal error: {str(e)}"}), 500
    
@app.route('/visualize')
def visualize():
    """Generate initial visualization"""
    visualize_graph()
    return jsonify({"status": "Visualization generated"})

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs("web", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)