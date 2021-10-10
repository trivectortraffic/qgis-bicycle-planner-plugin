import os.path
import sys

from devtools import debug
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsApplication

from bicycle_planner.ops import generate_od_routes
from bicycle_planner.utils import make_single, make_centroids


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

    bike_v, ebke_v = generate_od_routes(
        network_layer=network_layer,
        origins_source=deso_layer,
        dests_source=poi_layer,
        size_field='befolkning_191231',
        class_field='fclass',
        return_layer=False,
        return_raw=True,
    )
