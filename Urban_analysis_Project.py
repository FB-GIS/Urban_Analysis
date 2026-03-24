
# =============================================================================
# URBAN QUALITY OF LIFE INDEX — MARSEILLE DISTRICTS
# =============================================================================
# Computes a composite quality-of-life index for each of the 16 arrondissements
# of Marseille using OpenStreetMap data (via OSMnx).
# Each district is characterized by 10 urban indicators (densities / coverages),
# normalized and aggregated into a single weighted index.
# =============================================================================


# --- Imports -----------------------------------------------------------------

import geopandas as gpd
import shapely
import pandas as pd
import osmnx as ox
from sklearn.preprocessing import MinMaxScaler
import session_info
import overpy
import matplotlib.pyplot as plt
import os
import contextily as ctx
from collections import Counter
import re



# =============================================================================
# STEP 1 — DATA COLLECTION
# =============================================================================



def get_place_profile(place):
    
    """
    Downloads and saves OpenStreetMap features for a given place (district).
 
    For each thematic category (transport, green spaces, health, education,
    safety, commerce), OSM features are queried and saved as GeoJSON files
    in a dedicated folder under data/<place>/.
 
    Parameters
    ----------
    place : str
        Name of the district as recognized by OSM geocoder
        (e.g. '1er arrondissement, Marseille').
    """
    
    # Create output folder for this district if it does not exist
        
    folderout = 'data/' + place
    if not os.path.exists(folderout):
        os.makedirs(folderout)
        
        
    # --- Transport ---
    # Download the full road network (all types) and public transport features
    
    roads = ox.graph_from_place(place, network_type='all')
    public_transport = ox.features_from_place(place, tags={'public_transport':True}) 
    ox.save_graphml(roads, filepath = folderout + '/roads.graphml')
    public_transport.to_file(folderout + '/public_transport.geojson', driver='GeoJSON')
    
    # --- Green spaces ---
    
    parks = ox.features_from_place(place, tags={'leisure':'park'})
    recreation = ox.features_from_place(place, tags={'leisure':['recreation_ground', 'pitch']})  
    parks.to_file(folderout + '/parks.geojson', driver='GeoJSON')
    recreation.to_file(folderout + '/recreation.geojson', driver='GeoJSON')
    
    # --- Health & Education ---
    
    healthcare = ox.features_from_place(place, tags={'amenity':['hospital', 'pharmacy']})
    education = ox.features_from_place(place, tags={'amenity':['school', 'university']})    
    healthcare.to_file(folderout + '/healthcare.geojson', driver='GeoJSON')
    education.to_file(folderout + '/education.geojson', driver='GeoJSON')
    
     # --- Safety & Lighting ---
        
    emergency_services = ox.features_from_place(place, tags={'amenity':['police', 'fire_station', 'clinic']})
    street_light = ox.features_from_place(place, tags={'highway':['street_lamp']})
    emergency_services.to_file(folderout + '/emergency_services.geojson', driver='GeoJSON')
    street_light.to_file(folderout + '/street_light.geojson', driver='GeoJSON')
    
    # --- Economy ---
    
    commerce = ox.features_from_place(place, tags={'shop': True})
    employment_centers = ox.features_from_place(place, tags={'office': True, 'industrial': True})
    commerce.to_file(folderout + '/commerce.geojson', driver='GeoJSON')
    employment_centers.to_file(folderout + '/employment_centers.geojson', driver='GeoJSON')


# --- Run data collection for all 16 Marseille districts ---------------------


# Build district name list: '1er', '2e', ..., '16e'
district_numbers = [f"{i}{'er' if i < 2 else 'e'}" for i in range(1, 17)]

for dn in district_numbers:
    place = dn + ' arrondissement, Marseille'
     # Geocode the district boundary and save it as a GeoJSON polygon
    admin_d = ox.geocode_to_gdf(place)
    get_place_profile(place)
    admin_d.to_file('data/' + place + '/admin_boundaries.geojson', driver='GeoJSON')



# =============================================================================
# STEP 2 — DISTRICT CHARACTERIZATION
# =============================================================================



def characterize_district(place) :
    
    """
    Computes 10 urban indicators for a given district from saved GeoJSON files.
 
    All indicators are expressed as densities (count or area per km²),
    allowing fair comparison between districts of different sizes.
 
    Parameters
    ----------
    place : str
        Name of the district (must match the folder name under data/).
 
    Returns
    -------
    pd.DataFrame
        Single-row DataFrame containing the 10 computed indicators.
    """

    folderin = 'data/' + place
    
    # Load all previously saved spatial datasets
    roads_graph = ox.load_graphml(folderin + '/roads.graphml')
    parks = gpd.read_file(folderin + '/parks.geojson')
    recreation = gpd.read_file(folderin + '/recreation.geojson')
    public_transport = gpd.read_file(folderin + '/public_transport.geojson')
    healthcare = gpd.read_file(folderin + '/healthcare.geojson')
    education = gpd.read_file(folderin + '/education.geojson')
    emergency_services = gpd.read_file(folderin + '/emergency_services.geojson')
    street_lighting = gpd.read_file(folderin + '/street_light.geojson')
    commerce = gpd.read_file(folderin + '/commerce.geojson')
    employment_centers = gpd.read_file(folderin + '/employment_centers.geojson')
    
    # Use RGF93 / Lambert-93 (EPSG:2154) for accurate metric area computation in France
    crs = 2154
    
     # Extract road edges from the graph and compute total road length (km)
    edges = ox.graph_to_gdfs(roads_graph, nodes=False, edges=True)
    road_length = edges['length'].sum() / 1000
    
    # Estimate district area (km²) using the convex hull of the road network extent
    # Note: convex hull is an approximation — actual admin boundary would be more precise
    total_area = edges.to_crs(crs).union_all().convex_hull.area/1000**2
    
    # --- Compute indicators (normalized by district area) ---
    road_density = road_length/total_area  # km of road per km²
    public_transport_density = len(public_transport) / total_area # stops per km²
    
    park_coverage = (parks.to_crs(crs).area.sum()) / 1000**2 / total_area  # ratio [0-1]
    recreation_density = len(recreation) / total_area  # features per km²
    
    healthcare_accesibility = len(healthcare) / total_area # facilities per km²
    education_accessibility = len(education) / total_area # facilities per km²
    
    emergency_services_density = len(emergency_services) / total_area  # facilities per km²
    street_lighting_density = len(street_lighting) / total_area  # lamps per km²
    
    commerce_density = len(commerce) / total_area  # shops per km²
    employment_centers_density = len(employment_centers) / total_area  # offices per km²

    # Compile all indicators into a dictionary and return as a DataFrame row
    data = {
        'place' : place,
        'Road Density' : road_density,
        'Public Transport Density' : public_transport_density,
        'Park Coverage' : park_coverage,
        'Recreation Density' : recreation_density,
        'Healthcare Accesibility' : healthcare_accesibility,
        'Education Accessibility' : education_accessibility,
        'Emergency Services Density' : emergency_services_density,
        'Street Lighting Density' : street_lighting_density,
        'Commerce Density' : commerce_density,
        'Employment Centers Density' : employment_centers_density
    }
    
    df = pd.DataFrame([data]) 
    
    return df



# --- Run characterization for all districts and concatenate results ----------
districts = [f for f in os.listdir('data') if '.' not in f]

df_all = []

for district in districts :
    df = characterize_district(district)
    print(district, len(df))
    df_all.append(df)

# Concatenate all district rows into a single DataFrame indexed by district name
df_all = pd.concat(df_all).set_index('place')



# --- Correlation matrix — exploratory check ---------------------------------
# High correlations between indicators may suggest redundancy
# (e.g. healthcare and commerce density are strongly correlated at ~0.96)

df_all.corr()


# =============================================================================
# STEP 3 — INDEX COMPUTATION
# =============================================================================


df = df_all.copy()


# --- Load administrative boundaries for all districts -----------------------
gdf_admin = []

for district in os.listdir('data'):
    if '.DS' not in district: # Exclude macOS system files
        gdf = gpd.read_file('data/' + district + '/admin_boundaries.geojson')
        gdf['place'] = district
        gdf_admin.append(gdf)

gdf_admin = pd.concat(gdf_admin)



# --- Normalize all indicators to a [1, 10] scale ----------------------------
# MinMaxScaler rescales each column independently to the specified range

scaler = MinMaxScaler(feature_range=(1,10))

df_normalized = pd.DataFrame(
    scaler.fit_transform(df),
    columns = df.columns,
    index = df.index
)

df_normalized.head()



# --- Define indicator weights -----------------------------------------------
# Weights reflect the relative importance of each dimension in the final index.
# Public transport and commerce are weighted higher (0.15) as key urban drivers.
# All weights must sum to 1.0.

weights = {
    'Road Density': 0.1,
    'Public Transport Density': 0.15,
    'Park Coverage': 0.1,
    'Recreation Density': 0.1,
    'Healthcare Accesibility': 0.1,
    'Education Accessibility': 0.1,
    'Emergency Services Density': 0.1,
    'Street Lighting Density': 0.1,
    'Commerce Density': 0.15,
    'Employment Centers Density': 0.1
}



# Apply weights: multiply each indicator column by its corresponding weight

for feature in df_normalized.columns:
    df_normalized[feature] = df_normalized[feature] * weights[feature]



# Compute the Unified Index as the weighted sum of all indicators

df_normalized['Unified Index'] = df_normalized.sum(axis=1)

df_normalized[['Unified Index']]



# Re-normalize the Unified Index to [1, 10] for readability and round to integer

scaler = MinMaxScaler(feature_range=(1,10))

df_normalized['Unified Index'] = scaler.fit_transform(df_normalized[['Unified Index']])

df_normalized['Unified Index'] = df_normalized['Unified Index'].round(0)



# =============================================================================
# STEP 4 — VISUALIZATION
# =============================================================================



# --- Merge index with administrative boundaries for mapping -----------------

gdf_index = gdf_admin[['place', 'geometry']].merge(df_normalized[['Unified Index']], left_on='place', right_index=True)



# --- Choropleth map of the Unified Index across all 16 districts ------------
# Red = low quality of life, Green = high quality of life (RdYlGn color ramp)

f, ax = plt.subplots(1,1, figsize=(10,10))

gdf_index.plot(ax=ax, edgecolor='w', linewidth=1.5, alpha=0.9, column='Unified Index', cmap='RdYlGn', legend=True)

ax.axis('off');



# --- Bonus: Detailed building footprint map for a single district -----------
# Uses the last district boundary from the collection loop (admin_d)

admin_poly = admin_d.geometry.to_list()[0]

# Download all building footprints within the district boundary polygon
footprints = ox.features_from_polygon(admin_poly, tags={'building':True})

# Count and rank amenity types found within buildings (exploratory analysis)
Counter(footprints.dropna(subset=['amenity'])['amenity'].to_list()).most_common()



# --- Plot building footprints colored by amenity type -----------------------

crs_local = 2154  # RGF93 / Lambert-93 for accurate metric display

f, ax = plt.subplots(1,1, figsize=(10,10))

# District boundary outline
admin_d.to_crs(crs_local).plot(ax=ax, color='none', edgecolor='k', linewidth=2)

# All buildings in grey as background layer
footprints.to_crs(crs_local).plot(ax=ax, color='grey', alpha=0.5)

# Buildings with amenity tag colored by amenity type
footprints.to_crs(crs_local).plot(ax=ax, column='amenity', edgecolor='k', linewidth=0.3, cmap='tab20', legend=True)

# Add CartoDB Dark basemap for visual context
ctx.add_basemap(ax, crs = crs_local, source = ctx.providers.CartoDB.DarkMatterNoLabels)

# Zoom to district extent (hardcoded bounding box in Lambert-93 coordinates)
ax.set_ylim([6252000, 6255800.08])
ax.set_xlim([886727, 890700])

ax.axis('off');





