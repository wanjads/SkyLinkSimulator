import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# Pfad zur Datei
file_path = 'gs_file.txt'

# Einlesen der Koordinaten aus der Datei
df = pd.read_csv(file_path, header=None, names=['Longitude', 'Latitude'])

# Konvertiere den DataFrame in ein GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Latitude, df.Longitude))

# Weltkarte als Hintergrund laden
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

# Plot
fig, ax = plt.subplots(figsize=(15, 10))
world.plot(ax=ax, color='lightgrey')
gdf.plot(ax=ax, color='red', markersize=5)
plt.title('Städtekoordinaten weltweit')
plt.show()
