document.addEventListener('DOMContentLoaded', function() {
    const map = L.map('map').setView([38.7223, -9.1393], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    fetch('../data/processed/estradas_lisboa.geojson')
        .then(response => response.json())
        .then(roadsData => {
            L.geoJSON(roadsData, {
                style: {
                    color: '#666', // Road color
                    weight: 2,     // Line thickness
                    opacity: 0.7
                }
            }).addTo(map);
        })
        .catch(error => console.error('Error loading roads:', error));

    fetch('/data/processed/lisbon_taxi_ranks.geojson')
        .then(response => response.json())
        .then(data => {
            console.log('GeoJSON data:', data);
            const geoJsonLayer = L.geoJSON(data, {
                pointToLayer: (feature, latlng) => {
                    return L.marker(latlng, {
                        icon: L.icon({
                            iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41]
                        })
                    }).bindPopup(feature.properties.Nome_praca);
                }
            });
            geoJsonLayer.addTo(map); // Add the layer to the map
        })
        .catch(error => console.error('Error:', error));
});