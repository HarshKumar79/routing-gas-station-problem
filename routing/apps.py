from django.apps import AppConfig
import pandas as pd
from scipy.spatial import KDTree
import os

class RoutingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routing'
    
    # Class-level variables to hold our in-memory data
    fuel_df = None
    kdtree = None

    def ready(self):
        # Load the CSV when the app starts
        csv_path = os.path.join(os.path.dirname(__file__), 'geocoded_fuel_prices.csv')
        
        if os.path.exists(csv_path):
            # Read the CSV
            self.fuel_df = pd.read_csv(csv_path)
            
            # Ensure no missing coordinates break the tree
            self.fuel_df = self.fuel_df.dropna(subset=['Latitude', 'Longitude'])
            
            # Build the KDTree using (Latitude, Longitude)
            coords = list(zip(self.fuel_df['Latitude'], self.fuel_df['Longitude']))
            self.kdtree = KDTree(coords)
            print(f"Successfully loaded {len(self.fuel_df)} fuel stations into memory.")
        else:
            print("WARNING: geocoded_fuel_prices.csv not found in the routing app folder.")