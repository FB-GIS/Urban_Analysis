# Urban Quality of Life Index — Marseille Districts

## PROJECT OVERVIEW

This project computes a composite Urban Quality of Life Index for each of the 16 arrondissements (districts) of Marseille, France.  
Data is collected from OpenStreetMap via the OSMnx library, processed and  normalized, then aggregated into a single weighted index per district.  
Results are visualized as a choropleth map.  

#### BONUS :  
Creation of a simple Accessibility Index for each arrondissement of Marseille. This index combine some indicators - healthcare, recreation, public  transports, parks, emergency services, commerce, employment centers - at H3 hexagonal grid cells scale (resolution 9, ~105 m edge length).  


Livibility Index - Districts Visualization:  

![alt text](https://github.com/FB-GIS/Marseille_Urban_Livability_Index/blob/main/public/districts.png)  
    
      
(BONUS) Accessibility Index - H3 Visualization:  

![alt text](https://github.com/FB-GIS/Marseille_Urban_Livability_Index/blob/main/public/h3.png)  
    
    
## WORKFLOW

The analysis follows four main steps:  

  1. DATA COLLECTION (get_place_profile)  
     For each district, the following OSM features are downloaded and saved  
     as GeoJSON files under data/<district_name>/:  
       - roads.graphml            : road network (all types)  
       - public_transport.geojson : public transport stops/stations  
       - parks.geojson            : parks (leisure=park)  
       - recreation.geojson       : recreation grounds and pitches  
       - healthcare.geojson       : hospitals and pharmacies  
       - education.geojson        : schools and universities  
       - emergency_services.geojson : police, fire stations, clinics  
       - street_light.geojson     : street lamps  
       - commerce.geojson         : shops  
       - employment_centers.geojson : offices and industrial sites  
       - admin_boundaries.geojson : administrative boundary polygon  

  2. DISTRICT CHARACTERIZATION (characterize_district)  
     For each district, the following indicators are computed per unit area  
     (density or coverage ratio):  
       - Road Density              : total road length (km) / area (km²)  
       - Public Transport Density  : nb stops / area  
       - Park Coverage             : park area / total area  
       - Recreation Density        : nb recreation features / area  
       - Healthcare Accessibility  : nb healthcare facilities / area  
       - Education Accessibility   : nb education facilities / area  
       - Emergency Services Density: nb emergency facilities / area  
       - Street Lighting Density   : nb street lamps / area  
       - Commerce Density          : nb shops / area  
       - Employment Centers Density: nb offices/industrial / area  

  3. INDEX COMPUTATION

      1/ Livability Index : 
                
     - All indicators are normalized to a [1, 10] scale using MinMaxScaler.  
     - A weighted sum is applied to produce the Unified Index:  
         Road Density                : 0.10  
         Public Transport Density    : 0.15  
         Park Coverage               : 0.10  
         Recreation Density          : 0.10  
         Healthcare Accessibility    : 0.10  
         Education Accessibility     : 0.10  
         Emergency Services Density  : 0.10  
         Street Lighting Density     : 0.10  
         Commerce Density            : 0.15  
         Employment Centers Density  : 0.10  
     - The Unified Index is then re-normalized to [1, 10] and rounded.
    
  2/ Accessibility Index:  
  
  1. Polyfill each arrondissement with **H3 hexagonal cells** at resolution 9 (~105 m edge length, ~0.1 km²).  
  2. For each hexagon, measure the four indicators using **circular buffers**:  
       - **1,600 m radius** for healthcare, recreation, emergency services, commerce and employment centers (~20-min walk)  
       - **800 m radius** for parks and Public Transports (~10-min walk)  
  3. Apply Min-Max normalization.  
  4. Apply **H3 neighbor smoothing** using `h3.grid_disk(cell, k=2)` — each cell is averaged over its 2-ring neighborhood (up to 19 cells).  
  5. Re-normalize and compute the composite score.   
  
  ### Indicators  
  
  | Indicator | Measurement | Buffer (hex stage) |
  |---|---|---|  
  | Healthcare | Count | 1,600 m |  
  | Recreation| Count | 1,600 m |  
  | Public Transports | Count | 800 m |  
  | Parks | Total area (m²) | 800 m |   
  | Emergency Services| Count | 1,600 m | 
  | Commerce| Count | 1,600 m | 
  | Employment Centers| Count | 1,600 m |                                    
                      
                    
  5. VISUALIZATION  
     - Choropleth map for each Index (Livability and Accessibility) across all 16 districts  
       (RdYlGn color ramp — red = low quality, green = high quality).  


## DEPENDENCIES

  geopandas  
  pandas  
  osmnx  
  scikit-learn   (MinMaxScaler)  
  overpy  
  matplotlib  
  contextily  
  shapely  
  h3  
  h3pandas  
  leafmap  


## DATA

  Source   : OpenStreetMap (from OSMnx)  
  Spatial extent : 16 arrondissements of Marseille (1er to 16e)  


## NOTES

  - The index is relative : scores reflect ranking among the 16 districts,
    not absolute quality standards.
  - Weights are user-defined and can be adjusted in the weights dictionary
    to reflect different urban planning priorities.
