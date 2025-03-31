document.addEventListener('DOMContentLoaded', function() {
    // Initialize map with correct ID from HTML
    const map = L.map('map_ece8ba64fc57d466b6c9c8d3ab688d9d').setView([38.7223, -9.1393], 13);
    
    // Add tile layer with correct URL pattern and attribution
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        subdomains: 'abc'
    }).addTo(map);

    // State management
    let routeLayers = [];
    let depotMarker = null;
    let currentDepot = null;

    // Status display element
    const statusElement = document.createElement('div');
    Object.assign(statusElement.style, {
        position: 'absolute',
        top: '50px',
        right: '10px',
        padding: '8px',
        background: 'white',
        zIndex: '1000',
        borderRadius: '4px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
    });
    document.body.appendChild(statusElement);

    // Solve button handling
    const solveBtn = document.querySelector('button');
    solveBtn.disabled = true;
    solveBtn.removeAttribute('onclick');

    // Map click handler for depot placement
    map.on('click', async function(e) {
        try {
            clearRoutes();
            if (depotMarker) map.removeLayer(depotMarker);
            
            currentDepot = e.latlng;
            depotMarker = L.marker([currentDepot.lat, currentDepot.lng], {
                icon: L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41]
                })
            }).addTo(map);

            solveBtn.disabled = false;
            updateStatus(`Depot set at ${formatCoords(currentDepot)}. Click Solve VRP!`);
        } catch (error) {
            console.error('Depot error:', error);
            updateStatus('Error setting depot!', true);
        }
    });

    // Solve VRP handler with proper error handling
    solveBtn.addEventListener('click', async () => {
        try {
            if (!currentDepot) {
                updateStatus('Please set a depot first!', true);
                return;
            }

            updateStatus('Solving VRP...');
            
            const response = await fetch('/solve-vrp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    depot: {
                        lat: currentDepot.lat,
                        lng: currentDepot.lng
                    }
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Server error');
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                updateStatus(`Solved! ${data.routes.length} routes found.`);
                drawRoutes(data.routes);
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        } catch (error) {
            console.error('Solve error:', error);
            updateStatus(`Error: ${error.message}`, true);
        }
    });

    function drawRoutes(routes) {
        clearRoutes();
        const colors = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF'];
        
        routes.forEach((route, index) => {
            const routeLayer = L.polyline(route, {
                color: colors[index % colors.length],
                weight: 4,
                opacity: 0.7,
                smoothFactor: 1
            }).addTo(map);
            
            routeLayers.push(routeLayer);
        });
    }

    function clearRoutes() {
        routeLayers.forEach(layer => map.removeLayer(layer));
        routeLayers = [];
    }

    function updateStatus(message, isError = false) {
        statusElement.innerHTML = message;
        statusElement.style.color = isError ? '#dc3545' : '#28a745';
        statusElement.style.border = `1px solid ${isError ? '#dc3545' : '#28a745'}`;
    }

    function formatCoords(coords) {
        return `${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}`;
    }
});