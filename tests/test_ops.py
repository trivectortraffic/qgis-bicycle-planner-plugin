import os.path
import sys

from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsApplication

from bicycle_planner.ops import prepare_od_data, generate_od_routes, vectorize
from bicycle_planner.utils import make_single, make_centroids, print_mem


def test_foo_bar_baz(datadir, qgis_processing):

    net_path = os.path.join(datadir, 'net.fgb')
    deso_path = os.path.join(datadir, 'deso.fgb')
    poi_path = os.path.join(datadir, 'poi.fgb')

    network_layer = make_single(QgsVectorLayer(net_path, 'Network', 'ogr'))
    poi_layer = make_single(QgsVectorLayer(poi_path, 'POI', 'ogr'))
    deso_layer = make_centroids(make_single(QgsVectorLayer(deso_path, 'DeSO', 'ogr')))

    assert network_layer.isValid(), network_layer
    assert poi_layer.isValid(), poi_layer
    assert deso_layer.isValid(), deso_layer
    print_mem()

    origins_data, dests_data, od_data = prepare_od_data(
        deso_layer, poi_layer, 'befolkning_191231', 'fclass'
    )
    print_mem()

    features = generate_od_routes(
        network_layer=network_layer,
        origins_data=origins_data,
        dests_data=dests_data,
        od_data=od_data,
        return_layer=False,
    )
    print_mem()


def test_vectorize(datadir, qgis_processing):
    net_path = os.path.join(datadir, 'net.fgb')
    deso_path = os.path.join(datadir, 'deso.fgb')
    poi_path = os.path.join(datadir, 'poi.fgb')

    network_layer = make_single(QgsVectorLayer(net_path, 'Network', 'ogr'))
    poi_layer = make_single(QgsVectorLayer(poi_path, 'POI', 'ogr'))
    deso_layer = make_centroids(make_single(QgsVectorLayer(deso_path, 'DeSO', 'ogr')))

    assert network_layer.isValid(), network_layer
    assert poi_layer.isValid(), poi_layer
    assert deso_layer.isValid(), deso_layer

    vectorize(network_layer, deso_layer, poi_layer, 'befolkning_191231', 1)
