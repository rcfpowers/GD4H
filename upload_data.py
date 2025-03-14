import tkinter as tk
from tkinter import filedialog
import pandas as pd
import sys
import zipfile
import requests
import io
import os
import openrouteservice
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon, MultiPolygon, shape
from thefuzz import process  
import folium
import numpy as np
import time
from datetime import datetime

API_KEY_ORS = "5b3ce3597851110001cf6248e1c21942e51e45a9ba5e6081a595bc3d"  # Replace with your actual key
client = openrouteservice.Client(key=API_KEY_ORS)

def accept_user_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select a file", filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt")])
    
    if not file_path:
        sys.exit()
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.txt'):
        df = pd.read_csv(file_path, delimiter="\t")
    else:
        raise ValueError("Unsupported file format. Please provide a .csv or .txt file.")
    return df

def fuzzy_match_column(df, columns, default_col):
    best_match = None
    best_score = 0
    
    for col in columns:
        match, score = process.extractOne(col, df.columns)
        if score > best_score:
            best_match = match
            best_score = score
            
    if best_score < 70:
        match, score = process.extractOne(default_col, df.columns)
        if score < 70:
            print(f"No evident columns found. Please identify a {columns[0]} column")
            sys.exit(1)
        best_match = match
    return best_match

def identify_lat_long(df):
    predefined_lat = ['latitude', 'lat', 'lattitude', 'latitide', 'latitude_fr']
    predefined_lon = ['longitude', 'long', 'lng', 'longtitude', 'longitude_fr']
    predefined_loc = ['location', 'nom', 'name', 'landmark', 'title', 'building', 'site']
    predefined_cat = ['category', 'type', 'label', 'class', 'segment']

    best_match_lat = fuzzy_match_column(df, predefined_lat, 'x')
    best_match_long = fuzzy_match_column(df, predefined_lon, 'y')
    best_match_loc = fuzzy_match_column(df, predefined_loc, 'id')
    best_match_cat = fuzzy_match_column(df, predefined_cat, 'group')    
    
    df.rename(columns={best_match_lat: "latitude", best_match_long: "longitude", best_match_loc: "location", best_match_cat: "category"}, inplace=True)
    df["geometry"] = df.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)


def download_bpe():
    zip_url = 'https://www.insee.fr/fr/statistiques/fichier/8217525/BPE23.zip'
    response = requests.get(zip_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        file_name = z.namelist()[0]
        with z.open(file_name) as csv_file:
            df_bpe = pd.read_csv(csv_file, delimiter = ';')
    df_bpe.rename(columns={'LATITUDE': "latitude", 'LONGITUDE': "longitude", "NOMRS": "location", "DOM": "category"}, inplace=True)
    df_bpe = df_bpe.filter(items=["latitude","longitude","location","category","geometry"])
    df_bpe = df_to_geo(df_bpe)
    return df_bpe

def df_to_geo(df):
    df["geometry"] = df.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
    geo_df = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    return geo_df

def download_carreaus():
    #CARREAU_url = "https://www.insee.fr/fr/statistiques/fichier/6215138/Filosofi2017_carreaux_200m_shp.zip"
    REUN_file_path = "/Users/cpowers/Desktop/DEPP/In_Progress/EcoLab/GD4H/carreaus_reun.geojson"
    MART_file_path = "/Users/cpowers/Desktop/DEPP/In_Progress/EcoLab/GD4H/carreaus_mart.geojson"
    MET_file_path = "/Users/cpowers/Desktop/DEPP/In_Progress/EcoLab/GD4H/carreaus_met.geojson"
    
    if os.path.exists(MET_file_path):
        carreaus_geo = gpd.read_file(REUN_file_path)
    else:
        #shapefile_path_mart = "/Users/cpowers/Desktop/DEPP/In_Progress/EcoLab/GD4H/Filosofi2017_carreaux_200m_shp/Filosofi2017_carreaux_200m_mart.shp"
        #shapefile_path_reun = "/Users/cpowers/Desktop/DEPP/In_Progress/EcoLab/GD4H/Filosofi2017_carreaux_200m_shp/Filosofi2017_carreaux_200m_reun.shp"
        shapefile_path_met = "/Users/cpowers/Desktop/DEPP/In_Progress/EcoLab/GD4H/Filosofi2017_carreaux_200m_shp/Filosofi2017_carreaux_200m_met.shp"
        
        #carreaus_geo_mart = gpd.read_file(shapefile_path_mart)
        #carreaus_geo_mart = carreaus_geo_mart.to_crs(epsg=4326)
        
        #carreaus_geo_reun = gpd.read_file(shapefile_path_reun)
        #carreaus_geo_reun = carreaus_geo_reun.to_crs(epsg=4326)
        
        carreaus_geo_met = gpd.read_file(shapefile_path_met)
        carreaus_geo_met = carreaus_geo_met.to_crs(epsg=4326)
        
        carreaus_geo = gpd.GeoDataFrame(pd.concat([carreaus_geo_met], ignore_index=True))
        
        if "updated_at" not in carreaus_geo.columns:
            carreaus_geo["updated_at"] = np.nan
        
        carreaus_geo["longitude"] = carreaus_geo.geometry.centroid.x
        carreaus_geo["latitude"] = carreaus_geo.geometry.centroid.y

    return carreaus_geo

def map_carreaus_osrm(carr_geo, df):
    ORS_URL = "https://api.openrouteservice.org/v2/isochrones/"    
    transport_methods = ["driving-car", "cycling-regular", "foot-walking"]
    headers = {
    "Authorization": API_KEY_ORS,
    "Content-Type": "application/json"
    }
    
    #for mode in transport_methods:
        #carr_geo[f"{mode}_score"] = 0
    #selected_indices = [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009,1010,1011,1012,1013]
    
    query_count = 0
    for idx, row in carr_geo.iterrows(): #vectorize to run over columns
    
        if query_count <= 300 and pd.isna(row["updated_at"]):
            lat = row['latitude']
            lon = row['longitude']
        
            payload = {
            "locations": [[lon, lat]],
            "range": [900],
            "range_type": "time"
            }
        
            gdfs = []
            max_queries_per_day = 2500
            max_queries_per_minute = 40
            
            for mode in transport_methods:
                if query_count >= max_queries_per_day:
                    print("Daily API limit reached. Stopping queries.")
                    break
                if query_count % max_queries_per_minute == 0 and query_count > 0:
                    print("Rate limit reached. Sleeping for 60 seconds.")
                    time.sleep(60)  # Pause for a minute to prevent exceeding the per-minute limit
                travel_url = f"{ORS_URL}{mode}"
                osrm_response = requests.post(travel_url, json=payload, headers=headers)
                query_count += 1
                if osrm_response.status_code != 200:
                    print(f"Error for {mode}: {osrm_response.text}")
                    carr_geo.at[idx, f"{mode}_score"] = None
                    continue
                isochrone_geojson = osrm_response.json()["features"][0]["geometry"]
                isochrone_polygon = shape(isochrone_geojson)
                isochrone_gdf = gpd.GeoDataFrame({"transport_mode": [mode], "geometry": [isochrone_polygon]}, crs="EPSG:4326")
                gdfs.append(isochrone_gdf)
                
                carr_geo.at[idx, f"{mode}_score"] = df.geometry.within(isochrone_polygon).sum()
                carr_geo.at[idx, "updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            if gdfs:
                merged_isochrones_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
            else:
                merged_isochrones_gdf = None            
            
            #fig, ax = plt.subplots(figsize=(8, 8))
            #merged_isochrones_gdf.plot(ax=ax, edgecolor="red", facecolor="none", linestyle="--", label="OSRM Polygon")
            #ax.scatter(lon, lat, color="blue", marker="o", label="Centroid (Origin)")
            #plt.legend()
            #plt.show()
            
    
    #carr_geo_filtered = carr_geo.dropna(subset=["updated_at"])
    for mode in transport_methods:
        fig, ax = plt.subplots(figsize=(15, 15))  # Adjusted figure size for better visualization
        
        # Plot the filled polygons with scores
        carr_geo.plot(column=f"{mode}_score", ax=ax, cmap="OrRd", edgecolor="black", legend=True, alpha=0.7)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal") 
        
        # Titles and legends
        plt.title(f"Choropleth Map for {mode} Score", fontsize=14)
        plt.legend()
        
        plt.show()
    return carr_geo

#m = folium.Map(location=[2.3522, 48.8566], zoom_start=12)

#folium.GeoJson(isochrone_gdf, style_function=lambda x: {"color": "blue"}).add_to(m)

df_user = accept_user_file()
#def calculate_carreaus(df_user, weight_1, weight_2):
identify_lat_long(df_user)
df_user_geo = df_to_geo(df_user)
df_bpe = download_bpe()
carreaus = download_carreaus()
carreaus_copy = carreaus.copy()
carreaus = map_carreaus_osrm(carreaus_copy, df_bpe)
carreaus.to_file("/Users/cpowers/Desktop/DEPP/In_Progress/EcoLab/GD4H/carreaus_met.geojson", driver="GeoJSON")
gdf = gpd.GeoDataFrame(df_bpe, geometry="geometry", crs="EPSG:5794") #4326 - Europe
pd.set_option("display.max_columns", None)
#m.save("isochrone_map.html")
        
#m
        