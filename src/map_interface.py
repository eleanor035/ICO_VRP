import folium
from branca.element import MacroElement
from jinja2 import Template

class VRPMapInterface:
    def __init__(self, center=[38.7223, -9.1393]):
        self.map = folium.Map(center, zoom_start=13)
        self._add_click_handler()
        
    def _add_click_handler(self):
        """Add custom JS for click handling"""
        click_js = """
        function onClick(e) {
            let lat = e.latlng.lat;
            let lng = e.latlng.lng;
            fetch(`/set_depot?lat=${lat}&lng=${lng}`);
        }
        """
        self.map.add_child(folium.Element(f"""
            <script>{click_js}</script>
            <script>map.on('click', onClick);</script>
        """))
    
    def show(self):
        """Display or save the map"""
        self.map.save("web/templates/vrp_interface.html")