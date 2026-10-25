
"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const mapElement = document.getElementById("food-locations-map");
    const mapMessage = document.getElementById("map-message");
    const nearbyButton = document.getElementById("nearby-food-btn");
    const nearbyStatus = document.getElementById("nearby-status");

    // Update food expiry countdowns.
    function updateExpiryCountdowns() {
        document.querySelectorAll("[data-expiry]").forEach((element) => {
            const expiryDate = new Date(element.dataset.expiry);
            const difference = expiryDate.getTime() - Date.now();

            element.classList.remove(
                "expiry-critical",
                "expiry-urgent",
                "expiry-expired",
                "expiry-unknown"
            );

            if (Number.isNaN(expiryDate.getTime())) {
                element.textContent = "Expiry time unavailable";
                element.classList.add("expiry-unknown");
                return;
            }

            if (difference <= 0) {
                element.textContent = "⚠️ Expired";
                element.classList.add("expiry-expired");
                return;
            }

            const totalMinutes = Math.floor(difference / 60000);
            const days = Math.floor(totalMinutes / 1440);
            const hours = Math.floor((totalMinutes % 1440) / 60);
            const minutes = totalMinutes % 60;

            if (days > 0) {
                element.textContent = `⏳ ${days}d ${hours}h remaining`;
            } else if (hours > 0) {
                element.textContent = `⏳ ${hours}h ${minutes}m remaining`;
            } else {
                element.textContent = `⚠️ ${minutes}m remaining`;
            }

            if (difference < 60 * 60 * 1000) {
                element.classList.add("expiry-critical");
            } else if (difference < 24 * 60 * 60 * 1000) {
                element.classList.add("expiry-urgent");
            }
        });
    }

    updateExpiryCountdowns();
    window.setInterval(updateExpiryCountdowns, 60000);

    // Nearby Food button — works independently of the map.
    if (nearbyButton) {
        nearbyButton.addEventListener("click", () => {
            if (!navigator.geolocation) {
                if (nearbyStatus) {
                    nearbyStatus.textContent =
                        "Your browser does not support location access.";
                }
                return;
            }

            nearbyButton.disabled = true;

            if (nearbyStatus) {
                nearbyStatus.textContent = "Finding your location...";
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;

                    if (nearbyStatus) {
                        nearbyStatus.textContent =
                            "Location found! Sorting food by distance...";
                    }

                    const url = new URL(window.location.href);
                    url.searchParams.set("lat", latitude);
                    url.searchParams.set("lon", longitude);
                    window.location.assign(url.toString());
                },
                (error) => {
                    nearbyButton.disabled = false;

                    const messages = {
                        1: "Location permission denied. Allow location access in browser settings.",
                        2: "Your location could not be determined. Please try again.",
                        3: "Location request timed out. Please try again."
                    };

                    if (nearbyStatus) {
                        nearbyStatus.textContent =
                            messages[error.code] ||
                            "Unable to get your location. Please try again.";
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 60000
                }
            );
        });
    }

    // Read food locations from Django.
    let foodLocations = [];

    try {
        const dataElement = document.getElementById("food-map-data");
        foodLocations = JSON.parse(dataElement?.textContent || "[]");

        if (!Array.isArray(foodLocations)) {
            foodLocations = [];
        }
    } catch (error) {
        console.error("Could not read food location data:", error);
    }

    // Initialize the map.
    if (!mapElement) {
        console.error("Map container #food-locations-map was not found.");
        return;
    }

    if (typeof L === "undefined") {
        if (mapMessage) {
            mapMessage.textContent =
                "Map library failed to load. Check your internet connection and refresh.";
        }
        console.error("Leaflet (L) is not loaded.");
        return;
    }

    const map = L.map(mapElement).setView([20.5937, 78.9629], 5);

    // OpenStreetMap — no API key required.
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
        maxZoom: 19
    }).addTo(map);

    const markerGroup = L.featureGroup().addTo(map);

    foodLocations.forEach((food) => {
        const latitude = Number(food.latitude);
        const longitude = Number(food.longitude);

        if (
            !Number.isFinite(latitude) ||
            !Number.isFinite(longitude) ||
            latitude < -90 ||
            latitude > 90 ||
            longitude < -180 ||
            longitude > 180
        ) {
            return;
        }

        const marker = L.marker([latitude, longitude]);

        // Build popup safely without inserting raw HTML.
        const popup = document.createElement("div");

        const title = document.createElement("strong");
        title.textContent = food.name || "Available food";

        const location = document.createElement("p");
        location.textContent = food.location || "Location not provided";

        const quantity = document.createElement("p");
        quantity.textContent =
            `Quantity: ${food.quantity ?? "Not specified"}`;

        popup.append(title, location, quantity);

        if (food.distance_km !== null && food.distance_km !== undefined) {
            const distance = document.createElement("p");
            distance.textContent = `Distance: ${food.distance_km} km`;
            popup.appendChild(distance);
        }

        if (food.detail_url) {
            const link = document.createElement("a");
            link.href = food.detail_url;
            link.textContent = "View food details";
            popup.appendChild(link);
        }

        marker.bindPopup(popup);
        marker.addTo(markerGroup);
    });

    if (markerGroup.getLayers().length > 0) {
        map.fitBounds(markerGroup.getBounds().pad(0.15));

        if (markerGroup.getLayers().length === 1) {
            map.setZoom(Math.max(map.getZoom(), 12));
        }

        if (mapMessage) {
            mapMessage.textContent =
                `Showing ${markerGroup.getLayers().length} food location(s) on the map.`;
        }
    } else if (mapMessage) {
        mapMessage.textContent =
            "No food locations with valid coordinates are available yet.";
    }

    // Correct map layout if the map container was initially hidden.
    window.setTimeout(() => map.invalidateSize(), 100);
});
