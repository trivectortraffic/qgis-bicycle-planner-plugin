# This code aims to process the calculated shortest paths, applying gravity and destination choice models

import math
from datetime import datetime

import pandas as pd

# Shortest path algorithm based on Dijkstra's algorithm
# from Shortest_Path import Shortest_Path
import processing
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *

### Sigmoid fuction for mode choice ###


def sigmoid(b0, b1, b2, b3, X):
    X = float(X) / 30000
    try:
        S = 1 / (1 + math.exp(-(b0 + b1 * X + b2 * X ** 2 + b3 * math.sqrt(X))))
    except OverflowError:
        S = 'inf'
    return S


### Let's go!
print(datetime.now())

# purp_name = ['Leisure', 'Shopping', 'Services', 'Touring']
purp_name = ['Leisure']

# Dictionnaries for parameters
gravity_params = {
    'Leisure': -0.0351,
    'Shopping': -0.0833,
    'Services': -0.0833,
    'Touring': -0.0351,
}
mode_params_b = {
    'Shopping': [
        -0.44391129463248735,
        0.045421282463330465,
        -3.904112256228761,
        0.5687733506577125,
    ],
    'Services': [
        -8.295618349118543,
        -3.751848767649791,
        0.3791578463667172,
        -0.9215795742380404,
    ],
    'Touring': [
        -2.0871942229142797,
        -1.6994613073684237,
        -1.940943420795848,
        0.019770984624589937,
    ],
    'Leisure': [
        1.5641575146847442,
        -2.4196921105723215,
        5.526990391189266,
        -3.331767479111909,
    ],
}
mode_params_eb = {
    'Shopping': [
        -0.6498748953606043,
        -0.29797345841414963,
        -3.3602305317530834,
        -0.7290932553055972,
    ],
    'Services': [
        -3.1822681067845404,
        -2.1398819794608994,
        2.201028708826716,
        -1.4593795193621433,
    ],
    'Touring': [
        -0.976798293893275,
        -1.3330152115670482,
        -2.5280686380753137,
        -0.019578406245738936,
    ],
    'Leisure': [
        0.04333028543699834,
        -1.5403262612251727,
        4.310711954186476,
        -0.588298193854497,
    ],
}

origins = '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/origins.shp'

for i in range(len(purp_name)):
    name = purp_name[i]
    gravity = gravity_params[name]
    mode_b = mode_params_b[name]
    mode_eb = mode_params_eb[name]

    # 1. Join origin sizes to shortest path

    paths = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/Paths_'
        + name
        + '.shp'
    )
    processing.run(
        "native:joinattributestable",
        {
            'INPUT': paths,
            'FIELD': 'FromFID',
            'INPUT_2': origins,
            'FIELD_2': 'ID',
            'FIELDS_TO_COPY': ['Totalt'],
            'METHOD': 0,
            'DISCARD_NONMATCHING': False,
            'PREFIX': '',
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/WeightedPaths_'
            + name
            + '.shp',
        },
    )
    weighted_paths = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/WeightedPaths_'
        + name
        + '.shp'
    )

    # 2. Apply distance-decay functions

    work_layer = QgsVectorLayer(weighted_paths, '', 'ogr')
    work_layer.dataProvider().addAttributes(
        [QgsField("exp", QVariant.Double, "float", 8, 3)]
    )
    work_layer.dataProvider().addAttributes(
        [QgsField("fbike", QVariant.Double, "float", 8, 3)]
    )
    work_layer.dataProvider().addAttributes(
        [QgsField("febike", QVariant.Double, "float", 8, 3)]
    )
    work_layer.updateFields()

    features = work_layer.getFeatures()
    with edit(work_layer):
        for f in features:
            X = f['Distance']

            # Destination choice: exponential
            f['exp'] = math.exp(gravity * float(X) / 1000)

            # Mode choice probabilities
            f['fbike'] = sigmoid(mode_b[0], mode_b[1], mode_b[2], mode_b[3], X)
            f['febike'] = sigmoid(mode_eb[0], mode_eb[1], mode_eb[2], mode_eb[3], X)

            work_layer.updateFeature(f)

    processing.run(
        "qgis:statisticsbycategories",
        {
            'INPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/WeightedPaths_Leisure.shp',
            'VALUES_FIELD_NAME': 'exp',
            'CATEGORIES_FIELD_NAME': ['FromFID'],
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/Stats_'
            + name
            + '.csv',
        },
    )
    stats = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/Stats_'
        + name
        + '.csv'
    )
    stats_l = pd.read_csv(stats)

    stats_l.sort_values(by='FromFID')
    sum = stats_l['sum']

    request = qgis.core.QgsFeatureRequest()
    clause = qgis.core.QgsFeatureRequest.OrderByClause('FromFID', ascending=True)
    orderby = qgis.core.QgsFeatureRequest.OrderBy([clause])
    request.setOrderBy(orderby)

    work_layer.dataProvider().addAttributes(
        [QgsField("Tij", QVariant.Double, "float", 8, 3)]
    )
    work_layer.updateFields()

    index = 0
    fid = 1
    work_layer.startEditing()
    for f in work_layer.getFeatures(request):
        print('FID=', f['FromFID'])
        exp = f['exp']
        if f['FromFID'] != fid:
            fid = f['FromFID']
            index += 1
        sum_exp = sum[index]
        print(fid, exp / sum_exp)
        f['Tij'] = exp / sum_exp
        work_layer.updateFeature(f)
    work_layer.commitChanges()


print(datetime.now())
