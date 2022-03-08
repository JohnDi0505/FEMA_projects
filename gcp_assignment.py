import os
import re
import numpy as np
import geopandas as gpd
from shapely.ops import polygonize
from shapely.geometry import Point
from shapely.geometry import Polygon
from rasterio.enums import Resampling
from geocube.api.core import make_geocube
from shapely.geometry import MultiLineString

input_dir = "D:/Work/zf/0514-Trajectories"

grid_size = 500 #meter

crs_wgs1984 = 'epsg:3857'
crs_njsp = 'epsg:3424'
crs_utm18n = 'epsg:32618'


total_trajectory = np.empty(shape=(0,2))

for trajectory_file in os.listdir(input_dir):
    if re.search(r'(.+)-UTM.txt', trajectory_file):

        f_trajectory = open(input_dir + "/" + trajectory_file, 'r')
        p_trajectory = f_trajectory.readlines()

        downsample_coef = 100
        downsample_ix = np.arange(0, len(p_trajectory[33:]), downsample_coef)

        p_data = np.array([line.strip().split()[2:4] for line in p_trajectory[33:]])[downsample_ix.astype(int)].astype(float)
        total_trajectory = np.append(total_trajectory, p_data, axis=0)

        f_trajectory.close()

x_max = total_trajectory[:, 0].max()
x_min = total_trajectory[:, 0].min()
y_max = total_trajectory[:, 1].max()
y_min = total_trajectory[:, 1].min()

extent = gpd.GeoDataFrame(crs= crs_utm18n, geometry=[Polygon([(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min)])])
extent['exists'] = 1

cube = make_geocube(
    vector_data=extent,
    measurements=["exists"],
    resolution=(-1, 1),
    fill=np.nan,
).fillna(0)

reprojected = cube.rio.reproject(cube.rio.crs, resolution=grid_size, resampling=Resampling.average)


lon = reprojected.indexes['x']
lat = reprojected.indexes['y']

hlines = [((x1, yi), (x2, yi)) for x1, x2 in zip(lon[:-1], lon[1:]) for yi in lat]
vlines = [((xi, y1), (xi, y2)) for y1, y2 in zip(lat[:-1], lat[1:]) for xi in lon]

grids = list(polygonize(MultiLineString(hlines + vlines)))
grids_gdf = gpd.GeoDataFrame(crs=crs_utm18n, geometry=grids)

points = [Point(p) for p in total_trajectory]
points_gdf = gpd.GeoDataFrame(crs=crs_utm18n, geometry=points)

intersection = gpd.sjoin(points_gdf, grids_gdf, how='inner')
gcp_out = gpd.GeoDataFrame()
for grid in intersection.index_right.unique():
    temp = intersection.loc[intersection['index_right'] == grid, :]
    gcp_out = gcp_out.append(temp.sample())

gcp_out = gcp_out.reset_index(drop=True)
gcp_out.to_file("gcp0514.shp")