import os
import re
import shutil
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString

trajectory_CRS = "3424" # NJ State Plane

input_path = "X:/0520-2021/0520-trajectories"
output_path = "X:/0520-2021/las/airborne_control"
airborne_pc_path = "L:/Northeast_NJ_PostSandy_2014/PointCloud_NJ_StatePlane"
reference_path = "L:/Airborne_lidar_NJSP/Northeast_NJ/Northeast_NJ_postSandy_NJSP_surveyfeet.shp"

pc_tiles = gpd.read_file(reference_path)
#pc_tiles = pc_tiles.to_crs(epsg=trajectory_CRS)

os.listdir(input_path)

query_log = open(output_path + "/query.log", "w")

Total_trajectory = 0
for trajectory_file in os.listdir(input_path):
    if re.search(r'(.+)-NJSPSF.txt', trajectory_file):
        Total_trajectory += 1

n = 0
for trajectory_file in os.listdir(input_path):
    if re.search(r'(.+)-NJSPSF.txt', trajectory_file):
        trajectory_title = trajectory_file.replace("-NJSPSF.txt", "")

        # write .log file title
        query_log.write(trajectory_title + "\n")

        # create a folder for each path
        trajectory_copy_dir = output_path + "/" + trajectory_title
        if not os.path.isdir(trajectory_copy_dir):
            os.mkdir(trajectory_copy_dir)

        f_trajectory = open(input_path + "/" + trajectory_file, 'r')
        p_trajectory = f_trajectory.readlines()
        p_header = p_trajectory[29].strip().split(',')

        downsample_coef = 100
        downsample_ix = np.arange(0, len(p_trajectory[33:]), downsample_coef)

        p_data = np.array([line.strip().split() for line in p_trajectory[33:]])[downsample_ix.astype(int)].astype(float)

        lines = [LineString([Point(p_data[i, 2], p_data[i, 3]), Point(p_data[i + 1, 2], p_data[i + 1, 3])]) for i in
                 np.arange(len(p_data[:-1, 2:4]))]

        trajectory_gdf = gpd.GeoDataFrame(pd.DataFrame(lines, columns=['geoms']), geometry='geoms')
        trajectory_gdf = trajectory_gdf.set_crs(epsg=trajectory_CRS)

        # output trajectory for verification
        trajectory_out_shp = "G:/cd/zf_processing/gis/" + trajectory_title + ".shp"
        if not os.path.isfile(trajectory_out_shp):
            trajectory_gdf.to_file(trajectory_out_shp)

        # query airborne lidar
        airborne_query = gpd.sjoin(pc_tiles, trajectory_gdf, how='inner')

        if len(airborne_query) > 0:
            for pc_name in airborne_query.Tile_Name.unique():
                # copy point cloud (NJ State Plane) to destination folder
                original = airborne_pc_path + "/" + pc_name + ".las"
                target = trajectory_copy_dir + "/" + pc_name + ".las"
                if not os.path.isfile(target):
                    shutil.copyfile(original, target)
                    query_log.write(pc_name + "\n")
                else:
                    pass
        else:
            query_log.write("There is no airborne lidar coverage. \n")

        query_log.write("\n")

        f_trajectory.close()

        n += 1
        print("overall progress: %d / %d" % (n, Total_trajectory))

query_log.close()
