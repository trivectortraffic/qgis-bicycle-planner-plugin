"""
This code aims to do all the layer pre-processing (i.e. before calculating the shortest paths)
Its input are the network, the DeSO (origins) and the OSM POI (destinations)
"""

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

from .ops import generate_od_routes
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

    # 2. OSM data: separation by purpose
    # Creation of a new attribute
    with edit(poi_layer):
        if not poi_layer.addAttribute(QgsField('category', QVariant.String)):
            raise Exception('Failed to add layer attribute')

    poi_ids = {v: [] for v in poi_categories}
    poi_ids['unknown'] = []

    with edit(poi_layer):
        for feature in poi_layer.getFeatures():
            category = poi_class_map.get(feature['fclass'], 'unknown')
            feature['category'] = category
            poi_ids[category].append(feature.id())
            poi_layer.updateFeature(feature)

    POPULATION_FIELD = 'Totalt'
    CLASS_FIELD = 'fclass'
    origin_data = [
        (feature.id(), feature.geometry().asPoint(), feature[POPULATION_FIELD])
        for feature in origin_layer.getFeatures()
    ]

    destination_data = [
        (feature.id(), feature.geometry().asPoint(), feature['category'])
        for feature in poi_layer.getFeatures()
    ]

    with timing('calc rels using spatial index'):
        sindex = QgsSpatialIndex(poi_layer)
        od_data = []
        for feature in origin_layer.getFeatures():
            point = feature.geometry().asPoint()
            od_data.append(
                (
                    feature.id(),
                    sindex.nearestNeighbor(point, neighbors=9001, maxDistance=25000),
                )
            )

    # QgsProject.instance().addMapLayer(network_layer)
    # QgsProject.instance().addMapLayer(origin_layer)
    # QgsProject.instance().addMapLayer(poi_layer)

    # Sub layer for each category
    for category, category_fids in poi_ids.items():
        result_layer = generate_od_routes(
            network_layer=network_layer,
            origin_data=origin_data,
            destination_data=destination_data,
            od_data=od_data,
            use_dest_fids=category_fids,
            max_distance=30000,
            gravity_value=poi_gravity_values[category],
            bike_params=mode_params_bike[category],
            ebike_params=mode_params_ebike[category],
        )
        result_layer.setName(f'Result network for {category}')
        QgsProject.instance().addMapLayer(result_layer)

    ### Second part: give weights to the shortest paths calculated: see code OtherPurposes_2.py ###


if __name__ == '__main__':
    main()
