# This code aims to process the calculated shortest paths, applying gravity and destination choice models

import math
from datetime import datetime

# Shortest path algorithm based on Dijkstra's algorithm
# from Shortest_Path import Shortest_Path
from qgis import processing
from qgis.core import (
    edit,
    QgsField,
    QgsVectorLayer,
)
from PyQt5.QtCore import QVariant

from .params import poi_gravity_values, mode_params_bike, mode_params_ebike
from .utils import timing, sigmoid


@timing()
def main(iface):
    ### Let's go!
    print(datetime.now())

    purp_name = ['Leisure', 'Shopping', 'Services', 'Touring']
    # purp_name = ['Leisure']

    # Dictionnaries for parameters

    origins = '/tmp/origins.shp'

    for name in purp_name:
        gravity = poi_gravity_values[name]
        mode_b = mode_params_bike[name]
        mode_eb = mode_params_ebike[name]

        # 1. Join origin sizes to shortest path

        paths = '/tmp/Paths_' + name + '.shp'
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
                'OUTPUT': '/tmp/WeightedPaths_' + name + '.shp',
            },
        )
        weighted_paths = '/tmp/WeightedPaths_' + name + '.shp'

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

        X = processing.run(
            "native:fieldcalculator",
            {
                'INPUT': '/tmp/WeightedPaths_' + name + '.shp',
                'FIELD_NAME': 'Weight_bike',
                'FIELD_TYPE': 0,
                'FIELD_LENGTH': 0,
                'FIELD_PRECISION': 0,
                'FORMULA': 'Totalt*fbike*exp/sum(exp,FromFID)',
                'OUTPUT': 'TEMPORARY_OUTPUT',
            },
        )

        processing.run(
            "native:fieldcalculator",
            {
                'INPUT': X['OUTPUT'],
                'FIELD_NAME': 'Weight_ebike',
                'FIELD_TYPE': 0,
                'FIELD_LENGTH': 0,
                'FIELD_PRECISION': 0,
                'FORMULA': 'Totalt*febike*exp/sum(exp,FromFID)',
                'OUTPUT': '/tmp/WeightedPathsFinal_' + name + '.shp',
            },
        )
        weighted_paths_final = '/tmp/WeightedPathsFinal_' + name + '.shp'
        iface.addVectorLayer(weighted_paths_final, '', 'ogr')

    print(datetime.now())
