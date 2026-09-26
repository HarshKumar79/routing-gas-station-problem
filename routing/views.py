from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import polyline
import pandas as pd
from scipy.spatial import KDTree
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from django.conf import settings

# Global variables for in-memory spatial search
FUEL_DF = None
KDTREE = None

def load_fuel_data():
    """Loads the CSV and builds the KDTree only once."""
    global FUEL_DF, KDTREE
    if FUEL_DF is not None and KDTREE is not None:
        return True # Already loaded

    try:
        # Assuming geocoded_fuel_prices.csv is in the 'routing' app folder
        csv_path = os.path.join(settings.BASE_DIR, 'routing', 'geocoded_fuel_prices.csv')
        
        if not os.path.exists(csv_path):
            print(f"CRITICAL ERROR: CSV not found at {csv_path}")
            return False

        FUEL_DF = pd.read_csv(csv_path)
        FUEL_DF = FUEL_DF.dropna(subset=['Latitude', 'Longitude'])
        
        # Build KDTree
        coords = list(zip(FUEL_DF['Latitude'], FUEL_DF['Longitude']))
        KDTREE = KDTree(coords)
        print(f"SUCCESS: Loaded {len(FUEL_DF)} stations into KDTree.")
        return True
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return False

class FuelRouteAPIView(APIView):
    def get(self, request):
        # 1. Ensure Data is Loaded
        if not load_fuel_data():
            return Response({"error": "Fuel data is not available. Check server logs."}, status=500)

        start_location = request.query_params.get('start')
        finish_location = request.query_params.get('finish')

        if not start_location or not finish_location:
            return Response({"error": "Please provide both 'start' and 'finish' query parameters."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        # 2. Geocode
        geolocator = Nominatim(user_agent="fuel_routing_app_final")
        try:
            start_coord = geolocator.geocode(f"{start_location}, USA")
            finish_coord = geolocator.geocode(f"{finish_location}, USA")
            
            if not start_coord or not finish_coord:
                return Response({"error": "Could not geocode locations."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Geocoding error: {str(e)}"}, status=500)

        # 3. Get Route from OSRM
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{start_coord.longitude},{start_coord.latitude};{finish_coord.longitude},{finish_coord.latitude}?overview=full"
        response = requests.get(osrm_url)
        if response.status_code != 200:
            return Response({"error": "OSRM Routing API failed."}, status=502)
            
        route_data = response.json()
        if route_data.get('code') != 'Ok':
            return Response({"error": "No route found."}, status=404)

        route_info = route_data['routes'][0]
        geometry = route_info['geometry']
        total_distance_miles = route_info['distance'] * 0.000621371
        decoded_points = polyline.decode(geometry)

        # 4. Find Fuel Stops
        stops = []
        total_cost = 0.0
        miles_since_last_stop = 0
        last_point = decoded_points[0]
        
        MAX_SAFE_RANGE = 400 
        MPG = 10.0

        for point in decoded_points:
            segment_distance = geodesic(last_point, point).miles
            miles_since_last_stop += segment_distance
            last_point = point

            if miles_since_last_stop >= MAX_SAFE_RANGE:
                station = self.get_optimal_station_near(point)
                
                if station:
                    gallons = miles_since_last_stop / MPG
                    cost = gallons * station['Retail Price']
                    total_cost += cost
                    
                    station['gallons_filled'] = round(gallons, 2)
                    station['cost_for_leg'] = round(cost, 2)
                    stops.append(station)
                    miles_since_last_stop = 0 

        # 5. Final Leg
        if miles_since_last_stop > 0:
            final_price = stops[-1]['Retail Price'] if stops else 3.50 
            total_cost += (miles_since_last_stop / MPG) * final_price

        return Response({
            "start_location": start_location,
            "finish_location": finish_location,
            "total_distance_miles": round(total_distance_miles, 2),
            "total_fuel_cost_usd": round(total_cost, 2),
            "total_gallons_used": round(total_distance_miles / MPG, 2),
            "route_polyline": geometry,
            "fuel_stops": stops
        })

    def get_optimal_station_near(self, point):
        global FUEL_DF, KDTREE
        
        for radius_miles in [30, 50, 100]:
            radius_deg = radius_miles / 69.0
            indices = KDTREE.query_ball_point(point, r=radius_deg)
            
            if indices:
                nearby = FUEL_DF.iloc[indices]
                cheapest = nearby.loc[nearby['Retail Price'].idxmin()]
                return {
                    "Truckstop Name": cheapest.get('Truckstop Name'),
                    "Address": cheapest.get('Address'),
                    "City": cheapest.get('City'),
                    "State": cheapest.get('State'),
                    "Retail Price": float(cheapest.get('Retail Price')),
                    "Latitude": float(cheapest.get('Latitude')),
                    "Longitude": float(cheapest.get('Longitude'))
                }
        return None