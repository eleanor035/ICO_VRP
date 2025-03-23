// Initialize the map centered on Lisbon
const map = L.map('map').setView([38.7223, -9.1393], 13); // [lat, lng], zoom

// Add the OpenStreetMap tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);