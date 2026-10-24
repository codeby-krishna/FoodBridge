document.addEventListener("DOMContentLoaded", function () {
    // Elements
    const mapElement = document.getElementById("food-locations-map");
    const message = document.getElementById("map-message");
    const nearbyButton = document.getElementById("nearby-food-btn");
    const nearbyStatus = document.getElementById("nearby-status");
    const dataElement = document.getElementById("food-map-data");

    // 1. Find Food Near Me
    if (nearbyButton && nearbyStatus) {
        nearbyButton.addEventListener("click", function () {
            if (!navigator.geolocation) {
                nearbyStatus.textContent =
                    "Your browser does not support location access.";
                return;
            }

            nearbyButton.disabled = true;
            nearbyStatus.textContent = "Getting your current location...";

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    const params = new URLSearchParams(
                        window.location.search
                    );

                    params.set("lat", position.coords.latitude);
                    params.set("lon", position.coords.longitude);

                    nearbyStatus.textContent =
                        "Location found! Loading nearby food...";

                    const query = params.toString();
                    window.location.href =
                        window.location.pathname +
                        (query ? "?" + query : "");
                },
                function (error) {
                    nearbyButton.disabled = false;

                    if (error.code === error.PERMISSION_DENIED) {
                        nearbyStatus.textContent =
                            "Location permission denied. Allow location in your browser settings.";
                    } else if (error.code === error.TIMEOUT) {
                        nearbyStatus.textContent =
                            "Location request timed out. Please try again.";
                    } else {
                        nearbyStatus.textContent =
                            "Could not get location. Please try again.";
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

    // 2. Food expiry countdown
    function updateFoodExpiryCountdowns() {
        const now = Date.now();

        document.querySelectorAll(
            ".expiry-countdown[data-expiry]"
        ).forEach(function (element) {
            const expiryTime = new Date(
                element.dataset.expiry
            ).getTime();

            element.classList.remove(
                "expiry-critical",
                "expiry-urgent",
                "expiry-expired"
            );

            if (!Number.isFinite(expiryTime)) {
                element.textContent = "Expiry time unavailable";
                return;
            }

            const remaining = expiryTime - now;

            if (remaining <= 0) {
                element.textContent = "⛔ Expired";
                element.classList.add("expiry-expired");
                return;
            }

            const totalMinutes = Math.floor(remaining / 60000);
            const days = Math.floor(totalMinutes / 1440);
            const hours = Math.floor((totalMinutes % 1440) / 60);
            const minutes = totalMinutes % 60;

            let timeText;

            if (days > 0) {
                timeText =
                    `${days} day(s), ${hours} hour(s) remaining`;
            } else if (hours > 0) {
                timeText =
                    `${hours} hour(s), ${minutes} min remaining`;
            } else {
                timeText = `${minutes} min remaining`;
            }

            if (remaining <= 6 * 60 * 60 * 1000) {
                element.textContent = `🔴 Critical — ${timeText}`;
                element.classList.add("expiry-critical");
            } else if (remaining <= 24 * 60 * 60 * 1000) {
                element.textContent = `🟠 Urgent — ${timeText}`;
                element.classList.add("expiry-urgent");
            } else {
                element.textContent = `🟢 Fresh — ${timeText}`;
            }
        });
    }

    updateFoodExpiryCountdowns();
    setInterval(updateFoodExpiryCountdowns, 60000);

    // 3. Initialize Leaflet map
    if (!mapElement || typeof L === "undefined") {
        if (message) {
            message.textContent =
                "Map could not load. Please refresh the page.";
        }
        console.error(
            "FoodBridge: Map element or Leaflet library is missing."
        );
        return;
    }

    // Read food location data
    let foodLocations = [];

    try {
        if (!dataElement) {
            throw new Error("Food map data element not found.");
        }

        foodLocations = JSON.parse(dataElement.textContent);

        if (!Array.isArray(foodLocations)) {
            throw new Error("Food map data must be an array.");
        }
    } catch (error) {
        if (message) {
            message.textContent = "Could not read food location data.";
        }
        console.error("FoodBridge map data error:", error);
        return;
    }

    // Default map center: New Delhi
    const map = L.map(mapElement).setView([28.6139, 77.2090], 11);

    // Map tiles
    L.tileLayer(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }
    ).addTo(map);

    // 4. Add food markers
    const bounds = [];

    foodLocations.forEach(function (food) {
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

        const marker = L.marker([latitude, longitude]).addTo(map);

        // Build popup safely
        const popup = document.createElement("div");
        const title = document.createElement("strong");

        title.textContent = food.name || "Available Food";
        popup.appendChild(title);

        const quantity = document.createElement("p");
        quantity.textContent =
            "Quantity: " + (food.quantity ?? "Not specified");
        popup.appendChild(quantity);

        const location = document.createElement("p");
        location.textContent =
            "Location: " + (food.location || "Not specified");
        popup.appendChild(location);

        if (
            food.distance_km !== null &&
            food.distance_km !== undefined &&
            food.distance_km !== ""
        ) {
            const distance = document.createElement("p");
            distance.textContent =
                "Distance: " + food.distance_km + " km";
            popup.appendChild(distance);
        }

        if (food.detail_url) {
            const link = document.createElement("a");
            link.href = food.detail_url;
            link.textContent = "View Food Details";
            popup.appendChild(link);
        }

        marker.bindPopup(popup);
        bounds.push([latitude, longitude]);
    });

    // 5. Fit map to available food locations
    if (bounds.length > 0) {
        map.fitBounds(bounds, {
            padding: [25, 25],
            maxZoom: 14
        });

        if (message) {
            message.textContent =
                "Showing " + bounds.length +
                " food location(s) on the map.";
        }
    } else if (message) {
        message.textContent =
            "No food locations with saved coordinates are available on the map yet.";
    }

    // Fix map sizing after page layout
    setTimeout(function () {
        map.invalidateSize();
    }, 300);

});