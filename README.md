# 🗺️ Optimal Fuel Routing API

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0+-092E20.svg?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/Django_REST_Framework-red.svg?logo=django)
![SciPy](https://img.shields.io/badge/SciPy-KDTree-0054A6.svg?logo=scipy&logoColor=white)

A high-performance Django REST API that calculates the most cost-effective fueling strategy for a road trip within the USA. 

Given a start and finish location, the API maps the route, identifies the cheapest fuel stops based on a strict **500-mile vehicle range**, and calculates the total fuel cost assuming **10 miles per gallon (MPG)**.

---

## 🚀 Key Features & Architectural Decisions

* **⚡ Lightning-Fast Spatial Queries (KDTree):** Instead of setting up a heavy PostGIS database for a static dataset, the 8,000+ fuel stations are loaded into a Pandas DataFrame and mapped to an in-memory `scipy.spatial.KDTree` on Django startup. This reduces geospatial "nearest neighbor" lookups to sub-milliseconds `O(log N)`.
* **🗺️ Minimal Map API Calls:** To optimize latency and reduce third-party dependencies, the API makes exactly **ONE** call to the free **OSRM (Open Source Routing Machine) API** to fetch the entire route geometry. All subsequent distance tracking and station mapping are calculated locally.
* **🛡️ Dynamic Fallback Algorithm:** The greedy algorithm attempts to refuel around the 400-mile mark. If no stations are found in sparse areas, it dynamically expands its search radius (30 -> 50 -> 100 miles) to ensure the vehicle never breaches the 500-mile maximum limit.
* **📍 Pre-Geocoded Dataset:** The original provided dataset (`fuel-prices-for-be-assessment.csv`) lacked coordinate data. To enable spatial mathematics, a custom Python script was used to pre-geocode all addresses via the OpenStreetMap Nominatim API. The resulting file (`geocoded_fuel_prices.csv`) is included in this repository.

---

## ⚙️ Installation & Setup

Follow these steps to run the API locally on your machine.

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git)
cd YOUR_REPO_NAME

```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

```

### 4. Run the Development Server

```bash
python manage.py runserver

```

> *Note: During startup, you will see a console message confirming that the CSV has been successfully loaded into the KDTree memory.*

---

## 🛣️ API Documentation

### **Calculate Route & Fuel Stops**

Returns the route details, total cost, polyline, and optimal fuel stops.

* **URL:** `/api/route/`
* **Method:** `GET`
* **Query Parameters:**
* `start` (string, required): Starting city/address (e.g., `New York, NY`)
* `finish` (string, required): Destination city/address (e.g., `Miami, FL`)



#### **Example Request**

```http
GET [http://127.0.0.1:8000/api/route/?start=New](http://127.0.0.1:8000/api/route/?start=New) York, NY&finish=Miami, FL

```

#### **Example Success Response (`200 OK`)**

```json
{
    "start_location": "New York, NY",
    "finish_location": "Miami, FL",
    "total_distance_miles": 1279.55,
    "total_fuel_cost_usd": 423.13,
    "total_gallons_used": 127.96,
    "route_polyline": "wqnwFzfubM@BJt@BN@D@Hd@xCBTFXNx...",
    "fuel_stops": [
        {
            "Truckstop Name": "LOVLEN FOODS",
            "Address": "US-58 & SR-615",
            "City": "Drewryville",
            "State": "VA",
            "Retail Price": 3.049,
            "Latitude": 36.7157055,
            "Longitude": -77.3063603,
            "gallons_filled": 40.01,
            "cost_for_leg": 121.98
        }
        // ... additional stops to cover the journey
    ]
}

```

---

## 🏭 Production Readiness (V2 Considerations)

While the in-memory KDTree approach is highly optimized for this static assessment dataset, deploying this to a live production environment would require:

1. **PostGIS Integration:** Real-world fuel prices update frequently. An in-memory tree is difficult to sync across multiple load-balanced server workers. Migrating to **PostgreSQL + PostGIS** would allow for safe concurrent price updates and complex relational filtering (e.g., finding a station with specific amenities).
2. **Detour Cost Calculation:** Currently, the algorithm assumes the station is strictly on the route. V2 would factor in the slight distance/cost detour required to reach the physical gas station off the highway.

---
