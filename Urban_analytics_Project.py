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



def get_place_profile(place):
    
    folderout = 'data/' + place
    if not os.path.exists(folderout):
        os.makedirs(folderout)
        
    roads = ox.graph_from_place(place, network_type='all')
    public_transport = ox.features_from_place(place, tags={'public_transport':True}) 
    ox.save_graphml(roads, filepath = folderout + '/roads.graphml')
    public_transport.to_file(folderout + '/public_transport.geojson', driver='GeoJSON')
    
    parks = ox.features_from_place(place, tags={'leisure':'park'})
    recreation = ox.features_from_place(place, tags={'leisure':['recreation_ground', 'pitch']})  
    parks.to_file(folderout + '/parks.geojson', driver='GeoJSON')
    recreation.to_file(folderout + '/recreation.geojson', driver='GeoJSON')
    
    healthcare = ox.features_from_place(place, tags={'amenity':['hospital', 'pharmacy']})
    education = ox.features_from_place(place, tags={'amenity':['school', 'university']})    
    healthcare.to_file(folderout + '/healthcare.geojson', driver='GeoJSON')
    education.to_file(folderout + '/education.geojson', driver='GeoJSON')
    
    emergency_services = ox.features_from_place(place, tags={'amenity':['police', 'fire_station', 'clinic']})
    street_light = ox.features_from_place(place, tags={'highway':['street_lamp']})
    emergency_services.to_file(folderout + '/emergency_services.geojson', driver='GeoJSON')
    street_light.to_file(folderout + '/street_light.geojson', driver='GeoJSON')
    
    commerce = ox.features_from_place(place, tags={'shop': True})
    employment_centers = ox.features_from_place(place, tags={'office': True, 'industrial': True})
    commerce.to_file(folderout + '/commerce.geojson', driver='GeoJSON')
    employment_centers.to_file(folderout + '/employment_centers.geojson', driver='GeoJSON')


district_numbers = [f"{i}{'er' if i < 2 else 'e'}" for i in range(1, 17)]

for dn in district_numbers:
    place = dn + ' arrondissement, Marseille'
    admin_d = ox.geocode_to_gdf(place)
    get_place_profile(place)
    admin_d.to_file('data/' + place + '/admin_boundaries.geojson', driver='GeoJSON')



def characterize_district(place) :
    folderin = 'data/' + place
    
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
    
    
    crs = 23700
    edges = ox.graph_to_gdfs(roads_graph, nodes=False, edges=True)
    road_length = edges['length'].sum() / 1000
    total_area = edges.to_crs(crs).union_all().convex_hull.area/1000**2
    road_density = road_length/total_area
    public_transport_density = len(public_transport) / total_area
    
    park_coverage = (parks.to_crs(crs).area.sum()) / 1000**2 / total_area
    recreation_density = len(recreation) / total_area
    
    healthcare_accesibility = len(healthcare) / total_area
    education_accessibility = len(education) / total_area
    
    emergency_services_density = len(emergency_services) / total_area
    street_lighting_density = len(street_lighting) / total_area
    
    commerce_density = len(commerce) / total_area
    employment_centers_density = len(employment_centers) / total_area

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



districts = [f for f in os.listdir('data') if '.' not in f]

df_all = []

for district in districts :
    df = characterize_district(district)
    print(district, len(df))
    df_all.append(df)

df_all = pd.concat(df_all).set_index('place')

df_all.corr()

df = df_all.copy()

gdf_admin = []

for district in os.listdir('data'):
    if '.DS' not in district:
        gdf = gpd.read_file('data/' + district + '/admin_boundaries.geojson')
        gdf['place'] = district
        gdf_admin.append(gdf)

gdf_admin = pd.concat(gdf_admin)

scaler = MinMaxScaler(feature_range=(1,10))

df_normalized = pd.DataFrame(
    scaler.fit_transform(df),
    columns = df.columns,
    index = df.index
)

df_normalized.head()

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


for feature in df_normalized.columns:
    df_normalized[feature] = df_normalized[feature] * weights[feature]



df_normalized['Unified Index'] = df_normalized.sum(axis=1)

df_normalized[['Unified Index']]


scaler = MinMaxScaler(feature_range=(1,10))

df_normalized['Unified Index'] = scaler.fit_transform(df_normalized[['Unified Index']])

df_normalized['Unified Index'] = df_normalized['Unified Index'].round(0)


gdf_index = gdf_admin[['place', 'geometry']].merge(df_normalized[['Unified Index']], left_on='place', right_index=True)


f, ax = plt.subplots(1,1, figsize=(10,10))

gdf_index.plot(ax=ax, edgecolor='w', linewidth=1.5, alpha=0.9, column='Unified Index', cmap='RdYlGn', legend=True)

ax.axis('off');

admin_poly = admin_d.geometry.to_list()[0]

footprints = ox.features_from_polygon(admin_poly, tags={'building':True})

Counter(footprints.dropna(subset=['amenity'])['amenity'].to_list()).most_common()

crs_local = 2154

f, ax = plt.subplots(1,1, figsize=(10,10))

admin_d.to_crs(crs_local).plot(ax=ax, color='none', edgecolor='k', linewidth=2)

footprints.to_crs(crs_local).plot(ax=ax, color='grey', alpha=0.5)
footprints.to_crs(crs_local).plot(ax=ax, column='amenity', edgecolor='k', linewidth=0.3, cmap='tab20', legend=True)

    
ctx.add_basemap(ax, crs = crs_local, source = ctx.providers.CartoDB.DarkMatterNoLabels)

ax.set_ylim([6252000, 6255800.08])
ax.set_xlim([886727, 890700])

ax.axis('off');
