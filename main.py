import re
import numpy as np
import datetime as dt
import pandas as pd
import geopandas as gpd
from operator import itemgetter
from shapely.geometry import Polygon

utc2eastern = dt.timedelta(hours = 5)

f_trajectory = open("D:/Work/Manville/Web Application/0906-p2-njsp-surveyfeet.txt", 'r')
p_trajectory = f_trajectory.readlines()
f_trajectory.close()

f_image = open("D:/Work/Manville/Web Application/0906-p2-img.txt", 'r')
p_image = f_image.readlines()
f_image.close()

# # parsing trajectory files
# p_date = re.search(r': (.+)', p_trajectory[15].strip()).group(1)
# date_str = dt.datetime.strptime(p_date, '%Y-%m-%d')
# start_time = date_str - dt.timedelta(days=date_str.isoweekday() % 7)
#
p_header = [name.lstrip() for name in p_trajectory[29].strip().split(',')]
p_data = np.array([line.strip().split() for line in p_trajectory[33:]])
trajectory_df = pd.DataFrame(p_data, columns=p_header).astype(float)
# trajectory_df['TIME'] = trajectory_df['TIME'] - 3600 * 24 * (date_str.isoweekday() % 7) # convert trajectory time to second of day
#
#
# def time_parser(s_of_week):
#     days = int(s_of_week / (3600 * 24))
#     hours = int((s_of_week - (3600 * 24) * days) / 3600)
#     minutes = int((s_of_week - (3600 * 24) * days - 3600 * hours) / 60)
#     seconds = s_of_week - (3600 * 24) * days - 3600 * hours - 60 * minutes
#     milliseconds = int((s_of_week - (3600 * 24) * days - 3600 * hours - 60 * minutes - seconds) * 1000)
#     t_delta = dt.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
#     return(hours)


# parsing image file names
param_ix = (4,6,8,9,10)
imgs = [itemgetter(*param_ix)(re.split('\s+', line.strip())) for line in p_image]
img_df = pd.DataFrame(imgs, columns=['name', 'sow', 'pulse', 'sod', 'cam'])
img_df['sow'] = img_df['sow'].str.replace("at:", "").astype(float)
img_df['pulse'] = img_df['pulse'].str.replace("puls:", "").astype(int)
img_df['sod'] = img_df['sod'].str.replace("abs:", "").astype(float)


# filter images
img_dict = {}

n = 0

for pulse in img_df["pulse"].unique():

    temp_df = img_df.loc[img_df["pulse"] == pulse, :]

    img_dict[pulse] = {}

    temp_T = 0
    cam_num = 0
    for temp_ix in temp_df.index:
        if temp_df.loc[temp_ix, 'cam'] not in img_dict[pulse]:
            img_dict[pulse][temp_df.loc[temp_ix, 'cam']] = temp_df.loc[temp_ix, 'name']
            temp_T += temp_df.loc[temp_ix, 'sod']
            cam_num += 1

    img_dict[pulse]['trajectory_ix'] = np.argmin(np.abs(trajectory_df['TIME'] - temp_T / cam_num))

    n += 1

    print(n)


cam_info_out = pd.DataFrame(img_dict).T
trajectory_info_out = trajectory_df.loc[np.array(cam_info_out['trajectory_ix']), :].reset_index(drop=True)

gdf = gpd.GeoDataFrame(trajectory_info_out, geometry=gpd.points_from_xy(trajectory_info_out.LATITUDE, trajectory_info_out.LONGITUDE))

gdf.loc[np.arange(0, len(gdf), 10), :].reset_index(drop=True).to_file("Manville_0906-p2_latlon.json", driver='GeoJSON')


# Parsing each data point as arrow
def Arrow_Generator(origin, heading):
    tail_angle = 0.6 * np.pi
    head_len = 8 # feet
    tail_len = 3 # feet

    heading_in_pi = heading / 180 * np.pi
    head2tail_in_pi = (2 * np.pi - tail_angle) / 2
    tail_left_heading = heading_in_pi - head2tail_in_pi
    tail_right_heading = tail_left_heading - tail_angle

    head_coord = [origin[0] + head_len * np.sin(heading_in_pi), origin[1] + head_len * np.cos(heading_in_pi)]
    left_tail_coord = [origin[0] + tail_len * np.sin(tail_left_heading), origin[1] + tail_len * np.cos(tail_left_heading)]
    right_tail_coord = [origin[0] + tail_len * np.sin(tail_right_heading), origin[1] + tail_len * np.cos(tail_right_heading)]

    arrow_poly = Polygon([origin, left_tail_coord, head_coord, right_tail_coord])

    # generate field of view (75 x 58 degree) polygon for z+f map cams
    view_dist = 50 # feet
    fov_in_pi = 75 / 180 * np.pi
    left_cam_angle = heading_in_pi - 0.5 * np.pi
    right_cam_angle = heading_in_pi + 0.5 * np.pi
    rear_cam_angle = heading_in_pi - np.pi

    left_cam_pt_A = [origin[0] + view_dist * np.sin(left_cam_angle - fov_in_pi / 2), origin[1] + view_dist * np.cos(left_cam_angle - fov_in_pi / 2)]
    left_cam_pt_B = [origin[0] + view_dist * np.sin(left_cam_angle + fov_in_pi / 2), origin[1] + view_dist * np.cos(left_cam_angle + fov_in_pi / 2)]

    right_cam_pt_A = [origin[0] + view_dist * np.sin(right_cam_angle - fov_in_pi / 2),
                     origin[1] + view_dist * np.cos(right_cam_angle - fov_in_pi / 2)]
    right_cam_pt_B = [origin[0] + view_dist * np.sin(right_cam_angle + fov_in_pi / 2),
                     origin[1] + view_dist * np.cos(right_cam_angle + fov_in_pi / 2)]

    rear_cam_pt_A = [origin[0] + view_dist * np.sin(rear_cam_angle - fov_in_pi / 2),
                      origin[1] + view_dist * np.cos(rear_cam_angle - fov_in_pi / 2)]
    rear_cam_pt_B = [origin[0] + view_dist * np.sin(rear_cam_angle + fov_in_pi / 2),
                      origin[1] + view_dist * np.cos(rear_cam_angle + fov_in_pi / 2)]

    left_cam = Polygon([origin, left_cam_pt_A, left_cam_pt_B])
    right_cam = Polygon([origin, right_cam_pt_A, right_cam_pt_B])
    rear_cam = Polygon([origin, rear_cam_pt_A, rear_cam_pt_B])

    return(arrow_poly, left_cam, rear_cam, right_cam)


arrow, l_cam, b_cam, r_cam = Arrow_Generator([0, 0], gdf.loc[5, 'HEADING'])
gpd.GeoSeries(arrow).plot()
gpd.GeoSeries(l_cam).plot()
gpd.GeoSeries(b_cam).plot()
gpd.GeoSeries(r_cam).plot()