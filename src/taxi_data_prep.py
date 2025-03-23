import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


#xlsx to csv
df = pd.read_excel('data\\raw\\Praças de Táxis Lisboa.xlsx', engine='openpyxl')
df.to_csv('data\\processed\\pracas_taxis_lisboa.csv', index=False, encoding='utf-8')
print(df.head())
df['Longitude'] = df['Longitude'].astype(float)


#csv to geojson
geometry = [Point(lon, lat) for lon, lat in zip(df.Longitude, df.Latitude)]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
gdf.to_file("data\\processed\\lisbon_taxi_ranks.geojson", driver="GeoJSON")

