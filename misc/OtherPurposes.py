"""
This code aims to do all the layer pre-processing (i.e. before calculating the shortest paths)
Its input are the network, the DeSO (origins) and the OSM POI (destinations)
"""
from collections import namedtuple

from qgis import processing
from qgis.core import (
    edit,
    QgsField,
    QgsVectorLayer,
    QgsProcessing,
    QgsProject,
    QgsFeatureRequest,
    QgsSpatialIndex,
)
from PyQt5.QtCore import QVariant

from .ops import prepare_od_data, generate_od_routes
from .utils import timing, clone_layer, ensure_singlepart
from .params import (
    poi_class_map,
    poi_categories,
    poi_gravity_values,
    mode_params_bike,
    mode_params_ebike,
)


@timing()
def main():
    poi_path = '/tmp/small_poi.shp'
    network_path = '/tmp/small_net.shp'
    origins_path = '/tmp/origins.shp'

    ### First part: prepare data for the shortest path calculations, run the shortest path algorithm ###
    # 0. Make sure we have single parts
    poi_layer = processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': poi_path,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
        },
    )['OUTPUT']
    network_layer = processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': network_path,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
        },
    )['OUTPUT']
    origin_layer = clone_layer(QgsVectorLayer(origins_path, 'DESO centroids'))

    # 1. Creation of centroids for DeSO
    # deso = '/Users/laurentcazor/Documents/Trivector work/Data/Befolkning_2013_2018_shp__12f99f76-aa2f-40a9-a23b-06f3f08a10bf_/B1DesoSW_20181231/B1DeSO_SW_region.shp'
    # processing.run(
    #    "native:centroids",
    #    {
    #        'INPUT': deso,
    #        'ALL_PARTS': False,
    #        'OUTPUT': '/tmp/origins.shp',
    #    },
    # )

    origins_data, dests_data, od_data = prepare_od_data(
        origin_layer, poi_layer, 'Totalt', 'fclass'
    )

    result_layer = generate_od_routes(
        network_layer=network_layer,
        origins_data=origins_data,
        dests_data=dests_data,
        od_data=od_data,
    )
    result_layer.setName('Result network')
    QgsProject.instance().addMapLayer(result_layer)


if __name__ == '__main__':
    main()
