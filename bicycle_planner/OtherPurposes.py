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
    ### First part: prepare data for the shortest path calculations, run the shortest path algorithm ###
    # 0. Make sure we have single parts
    processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': '/tmp/small_poi.shp',
            'OUTPUT': '/tmp/small_poi_s.shp',
        },
    )
    processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': '/tmp/small_net.shp',
            'OUTPUT': '/tmp/small_net_s.shp',
        },
    )

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

    poi_path = '/tmp/small_poi_s.shp'
    network_path = '/tmp/small_net_s.shp'
    origins_path = '/tmp/origins.shp'

    point_id = 9000

    # 2. OSM data: separation by purpose
    # Creation of a new attribute

    network_layer = clone_layer(QgsVectorLayer(network_path, 'Road network'))

    poi_layer = clone_layer(QgsVectorLayer(poi_path, 'Points of Interest'))
    print(poi_layer)
    with edit(poi_layer):
        if not poi_layer.addAttribute(QgsField('category', QVariant.String)):
            raise Exception('Failed to add layer attribute')
        if not poi_layer.addAttribute(QgsField('point_id', QVariant.Int)):
            raise Exception('Failed to add layer attribute')

    poi_ids = {v: [] for v in poi_categories}
    poi_ids['unknown'] = []

    print(poi_layer)
    print(poi_ids)

    with edit(poi_layer):
        for feature in poi_layer.getFeatures():
            category = poi_class_map.get(feature['fclass'], 'unknown')
            feature['category'] = category
            feature['point_id'] = point_id
            poi_ids[category].append(feature.id())
            poi_layer.updateFeature(feature)

            point_id += 1

    # 3. Creation of the point layers with a unique ID

    # 3.1 Unique ID for DeSO

    origin_layer = clone_layer(QgsVectorLayer(origins_path, 'DESO centroids'))
    with edit(origin_layer):
        if not origin_layer.addAttribute(QgsField('point_id', QVariant.Int)):
            raise Exception('Failed to add layer attribute')

    with edit(origin_layer):
        for feature in origin_layer.getFeatures():
            feature['point_id'] = point_id
            origin_layer.updateFeature(feature)

            point_id += 1

    # 3.2 Creation of Unique ID for all the destinations

    # QgsProject.instance().addMapLayer(network_layer)
    # QgsProject.instance().addMapLayer(origin_layer)
    # QgsProject.instance().addMapLayer(poi_layer)

    # Sub layer for each category
    for category, ids in poi_ids.items():
        cat_poi_layer = poi_layer.materialize(QgsFeatureRequest().setFilterFids(ids))
        cat_poi_layer.setName(f'PoI for {category}')

        # 3.3 Merge layers
        od_layer = processing.run(
            "native:union",
            {
                'INPUT': cat_poi_layer,
                'OVERLAY': origin_layer,
                'OVERLAY_FIELDS_PREFIX': 'D_',
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            },
        )['OUTPUT']
        od_layer.setName(f'Combined PoI and DESO for {category}')
        print(od_layer)
        with edit(od_layer):
            for feature in od_layer.getFeatures():
                feature['point_id'] = feature['point_id'] or feature['D_point_id']
                od_layer.updateFeature(feature)

        # 4. Creation of a relation layer: origins and destinations which are not too far

        relations_data = QgsVectorLayer(
            processing.run(
                "saga:pointdistances",
                {
                    'POINTS': origin_layer,
                    'ID_POINTS': 'point_id',
                    'NEAR': cat_poi_layer,
                    'ID_NEAR': 'point_id',
                    'FORMAT': 1,
                    'MAX_DIST': 25000,
                    'DISTANCES': QgsProcessing.TEMPORARY_OUTPUT,
                },
            )['DISTANCES'],
            'Relations data',
        )
        print(relations_data)

        # 5. Run the shortest path algorithm
        points_layer = ensure_singlepart(od_layer)
        points_layer.setName('Points')

        # QgsProject.instance().addMapLayer(cat_poi_layer)
        # QgsProject.instance().addMapLayer(od_layer)
        # QgsProject.instance().addMapLayer(points_layer)
        # QgsProject.instance().addMapLayer(relations_data)

        result_layer = generate_od_routes(
            network_layer=network_layer,
            points_layer=points_layer,
            relations_data=relations_data,
            origin_field='ID_POINT',
            destination_field='ID_NEAR',
            population_field='D_Totalt',
            max_distance=30000,
            crs=network_layer.crs(),
            gravity_value=poi_gravity_values[category],
            bike_params=mode_params_bike[category],
            ebike_params=mode_params_ebike[category],
        )
        result_layer.setName(f'Result graph for {category}')
        QgsProject.instance().addMapLayer(result_layer)

    ### Second part: give weights to the shortest paths calculated: see code OtherPurposes_2.py ###


if __name__ == '__main__':
    main()
