import math

import numpy as np

from .compute_ldv import compute_ldv
import re
import pandas as pd
from io import StringIO
import os
from numpy import ndarray, array
import time

class ldv:
    # type = 0 : epsilon LDV, para is relative error
    # type = 1 : tau LDV, para is threshold
    def __init__(self, csv_file=None, start_field=None, end_field=None, X=320, Y=240, bandwidth=1000, type=0, para=0.1, prjPath=None, feedback=None):
        '''
        dataset = "Beijing"
        method = 4  # LARGE + R-tree
        X = 320 # row pixels
        Y = 240 # colum pixels
        bandwidth = 1000 # Spatial bandwidth
        type = 0 # epsilon LDV
            para = 0.1 # relative error
        type = 1 # tau LDV
            para = 10 # threshold

        '''
        self.result = None
        self.ref_lat = None
        self.y_min = None
        self.x_min = None
        self.csv_file = csv_file
        self.start_field = start_field
        self.end_field = end_field
        self.type = type
        self.method = 4
        self.X = X
        self.Y = Y
        self.bandwidth = bandwidth

        self.para = para
        self.prjPath = prjPath
        self.txtPath = prjPath + "/temp/LDV/tempTxt"
        self.outputPath = prjPath + "/temp/LDV/output"
        self.feedback = feedback
    def set_args(self):

        df = pd.read_csv(self.csv_file)
        self.ref_lat, self.x_min, self.y_min = getConverted_df(self, df, self.start_field, self.end_field)

        self.args = [0,
                     self.txtPath,
                     self.outputPath,
                     self.method,
                     self.type,
                     self.X,
                     self.Y,
                     self.bandwidth,
                     self.para
                     ]
        self.args = [str(x).encode('ascii') for x in self.args]
        self.feedback.pushInfo('args: {}'.format(self.args))
    def compute(self):
        self.feedback.pushInfo('Start preprocess raw data')
        start = time.time()
        self.set_args()
        end = time.time()
        duration = end - start
        self.feedback.setProgress(40)
        self.feedback.pushInfo('End preprocess, duration:{}s'.format(duration))

        self.feedback.pushInfo('Start compute LDV ')
        start = time.time()
        ldv = compute_ldv(self.args)

        end = time.time()
        duration = end - start
        self.feedback.setProgress(80)
        self.feedback.pushInfo('End compute LDV, duration:{}s'.format(duration))

        result = pd.read_csv(StringIO(ldv), sep=' ', names=['x', 'y', 'val'])
        # self.feedback.pushInfo('ldv result:{}'.format(result))
        self.result = getInverted_result(result, self.ref_lat, self.x_min, self.y_min)
        return self.result

pi = math.pi
earth_radius = 6371000
inf = float('inf')
def convert_lon_lat_to_x_y(lon, lat, ref_lat):
    lon = lon * pi / 180
    lat = lat * pi / 180
    ref_lat = ref_lat * pi / 180
    x = earth_radius * lon * math.cos(ref_lat)
    y = earth_radius * lat
    return x, y


def convert_x_y_to_lon_lat(x, y, ref_lat):
    ref_lat = ref_lat * pi / 180
    lon = (180.0 * x) / (pi * earth_radius * math.cos(ref_lat))
    lat = (180.0 * y) / (pi * earth_radius)
    return lon, lat

def obtain_ref_lat(df):
    ref_lat = (df['start_latitude'].sum() + df['end_latitude'].sum()) / (2.0 * len(df))
    return ref_lat

def convert_coordinates(df):
    ref_lat = obtain_ref_lat(df)

    df[['start_x', 'start_y']] = df.apply(
        lambda row: convert_lon_lat_to_x_y(row['start_longitude'], row['start_latitude'], ref_lat),
        axis=1, result_type='expand'
    )

    df[['end_x', 'end_y']] = df.apply(
        lambda row: convert_lon_lat_to_x_y(row['end_longitude'], row['end_latitude'], ref_lat),
        axis=1, result_type='expand'
    )

    eps = 0.001
    mask = (np.abs(df['end_x'] - df['start_x']) >= eps) | (np.abs(df['end_y'] - df['start_y']) >= eps)
    df = df[mask]

    x_min = df[['start_x', 'end_x']].min().min()
    y_min = df[['start_y', 'end_y']].min().min()

    df['start_x'] -= x_min
    df['start_y'] -= y_min
    df['end_x'] -= x_min
    df['end_y'] -= y_min

    df.loc[np.abs(df['end_x'] - df['start_x']) < eps, 'end_x'] += 1.0

    return df[['start_x', 'start_y', 'end_x', 'end_y']], ref_lat, x_min, y_min

def getConverted_df(self, df, startPoint, endPoint):
    df['start_longitude'], df['start_latitude'] = zip(*df[startPoint].map(extract_coordinates))
    df['end_longitude'], df['end_latitude'] = zip(*df[endPoint].map(extract_coordinates))

    df = df[['start_longitude', 'start_latitude', 'end_longitude', 'end_latitude']]
    df = df.dropna(subset=['start_longitude', 'start_latitude', 'end_longitude', 'end_latitude'])

    converted_df, ref_lat, x_min, y_min = convert_coordinates(df)
    with open(self.txtPath, 'w') as f:
        f.write(str(len(converted_df)) + '\n')
        converted_df.to_csv(f, sep=' ', index=False, header=False)
    return ref_lat, x_min, y_min
def extract_coordinates(point):
    if not isinstance(point, str):
        point = str(point)
    match = re.match(r'POINT\s*\(\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*\)', point)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

def getInverted_result(result, ref_lat, x_min, y_min):
    result['x'] = result['x'] + x_min
    result['y'] = result['y'] + y_min
    result['lon'], result['lat'] = zip(
        *result.apply(lambda row: convert_x_y_to_lon_lat(row['x'], row['y'], ref_lat), axis=1))
    result['val'] = result['val'].clip(lower=0)
    return result[['lon', 'lat', 'val']]

