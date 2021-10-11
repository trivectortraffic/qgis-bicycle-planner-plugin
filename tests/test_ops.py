import os.path
import sys
import csv

from devtools import debug
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsApplication

from bicycle_planner.ops import generate_od_routes
from bicycle_planner.utils import make_single, make_centroids


def test_foo_bar_baz(datadir, qgis_processing):

    net_path = os.path.join(datadir, 'net.fgb')
    deso_path = os.path.join(datadir, 'deso.fgb')
    poi_path = os.path.join(datadir, 'poi.fgb')

    work_path = os.path.join(datadir, 'work_dest.fgb')

    socio_path = 'socio_status.csv'

    network_layer = make_single(QgsVectorLayer(net_path, 'Network', 'ogr'))
    poi_layer = make_single(QgsVectorLayer(poi_path, 'POI', 'ogr'))
    deso_layer = make_centroids(make_single(QgsVectorLayer(deso_path, 'DeSO', 'ogr')))

    work_layer = make_centroids(make_single(QgsVectorLayer(work_path, 'Work', 'ogr')))

    assert network_layer.isValid(), network_layer
    assert poi_layer.isValid(), poi_layer
    assert deso_layer.isValid(), deso_layer

    socio_data = None
    if os.path.exists(socio_path):
        with open(socio_path, 'r') as fp:
            reader = csv.reader(fp)
            header = next(reader)
            join_id = header[0]
            index_field = header.index('Index')
            socio_data = {row[0]: float(row[index_field]) for row in reader}

    bike_v, ebke_v = generate_od_routes(
        network_layer=network_layer,
        origin_layer=deso_layer,
        poi_layer=poi_layer,
        size_field='befolkning_191231',
        class_field='fclass',
        work_layer=work_layer,
        work_size_field='Totalt',
        socio_data=socio_data,
        return_layer=False,
        return_raw=True,
    )
