from datetime import datetime

import processing
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *

for i in range(2, 17):
    print(datetime.now())
    # Union of the layers
    processing.run(
        "native:union",
        {
            'INPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/O'
            + str(i)
            + '.shp',
            'OVERLAY': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/D'
            + str(i)
            + '.shp',
            'OVERLAY_FIELDS_PREFIX': 'D_',
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/Union_'
            + str(i)
            + '.shp',
        },
    )
    layer = iface.addVectorLayer(
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/Union_'
        + str(i)
        + '.shp',
        '',
        'ogr',
    )
    layer_p = layer.dataProvider()

    layer_p.addAttributes([QgsField('ID', QVariant.Int)])
    layer.updateFields()

    # Creation of only one field for the united layers
    with edit(layer):
        for f in layer.getFeatures():
            # Creation of a unique ID for each ruta
            f['ID'] = 1 + f.id()
            f['Ruta'] = max(f['D_Ruta'], f['Ruta'])
            layer.updateFeature(f)

    # Change to single point layers
    processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/Union_'
            + str(i)
            + '.shp',
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/UnionS_'
            + str(i)
            + '.shp',
        },
    )
    points_url = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/UnionS_'
        + str(i)
        + '.shp'
    )
    relations_url = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/OD'
        + str(i)
        + '.dbf|layername=OD'
        + str(i)
    )

    # Table join to have these IDs on the relation layer as well
    processing.run(
        "native:joinattributestable",
        {
            'INPUT': relations_url,
            'FIELD': 'ID_POINT',
            'INPUT_2': points_url,
            'FIELD_2': 'Ruta',
            'FIELDS_TO_COPY': ['ID'],
            'METHOD': 0,
            'DISCARD_NONMATCHING': False,
            'PREFIX': '',
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/RelationsTemp_'
            + str(i),
        },
    )
    new_relations = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/RelationsTemp_'
        + str(i)
        + '.gpkg|layername=RelationsTemp_'
        + str(i)
    )
    processing.run(
        "native:joinattributestable",
        {
            'INPUT': new_relations,
            'FIELD': 'ID_NEAR',
            'INPUT_2': points_url,
            'FIELD_2': 'Ruta',
            'FIELDS_TO_COPY': ['ID'],
            'METHOD': 0,
            'DISCARD_NONMATCHING': False,
            'PREFIX': '',
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/Relations_'
            + str(i),
        },
    )

    final_relations = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/Relations_'
        + str(i)
        + '.gpkg|layername=Relations_'
        + str(i)
    )
