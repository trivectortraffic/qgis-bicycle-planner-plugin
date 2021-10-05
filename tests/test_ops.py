import os.path
import sys

from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsApplication

from bicycle_planner.ops import prepare_od_data, generate_od_routes
from bicycle_planner.utils import make_single


def test_foo_bar_baz(datadir, qgis_processing):

    gpkg_path = os.path.join(datadir, 'sormland.gpkg')
    print(gpkg_path)

    network_layer = make_single(
        QgsVectorLayer(f'{gpkg_path}|layername=small_net', 'Network', 'ogr')
    )
    poi_layer = make_single(
        QgsVectorLayer(f'{gpkg_path}|layername=small_poi', 'Network', 'ogr')
    )
    deso_layer = make_single(
        QgsVectorLayer(f'{gpkg_path}|layername=small_deso', 'Network', 'ogr')
    )

    assert network_layer.isValid(), network_layer
    assert poi_layer.isValid(), poi_layer
    assert deso_layer.isValid(), deso_layer

    origins_data, dests_data, od_data = prepare_od_data(
        deso_layer, poi_layer, 'totalt', 'fclass'
    )

    features = generate_od_routes(
        network_layer=network_layer,
        origins_data=origins_data,
        dests_data=dests_data,
        od_data=od_data,
        return_layer=False,
    )
