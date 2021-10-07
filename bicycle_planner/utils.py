import math
import psutil


from contextlib import ContextDecorator
from time import time
from typing import Optional


from qgis import processing
from qgis.core import QgsVectorLayer, QgsProcessing, QgsWkbTypes

from .params import MAX_DISTANCE_M


def clone_layer(input_layer) -> QgsVectorLayer:
    input_layer.selectAll()
    output_layer = processing.run(
        'qgis:saveselectedfeatures',
        {'INPUT': input_layer, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},
    )['OUTPUT']
    input_layer.removeSelection()
    output_layer.setName(input_layer.name())
    return output_layer


def ensure_singlepart(input_url: str) -> QgsVectorLayer:
    return processing.run(
        'native:multiparttosingleparts',
        dict(
            INPUT=input_url,
            OUTPUT=QgsProcessing.TEMPORARY_OUTPUT,
        ),
    )['OUTPUT']


def make_single(input_layer, **kwargs) -> QgsVectorLayer:
    if QgsWkbTypes.isMultiType(input_layer.wkbType()):
        result = processing.run(
            'native:multiparttosingleparts',
            {
                'INPUT': input_layer,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            },
            **kwargs,
        )['OUTPUT']

        result_layer = (
            result
            if 'context' not in kwargs
            else kwargs['context'].takeResultLayer(result)
        )
    else:
        result_layer = input_layer

    return result_layer


def make_centroids(input_layer, **kwargs) -> QgsVectorLayer:
    geom_type = QgsWkbTypes.geometryType(input_layer.wkbType())
    if geom_type == QgsWkbTypes.PolygonGeometry:
        result = processing.run(
            'native:centroids',
            {
                'INPUT': input_layer,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            },
            **kwargs,
        )['OUTPUT']

        result_layer = (
            result
            if 'context' not in kwargs
            else kwargs['context'].takeResultLayer(result)
        )
    elif geom_type == QgsWkbTypes.PointGeometry:
        result_layer = input_layer
    else:
        raise Exception('Geometry must be Polygon or Point')

    return result_layer


def print_mem():
    mem_mib = psutil.Process().memory_info().rss / (1024 * 1024)
    print(f'{mem_mib:0.2f} MiB')


def make_deso_centroids(input_url: str) -> QgsVectorLayer:
    processing.run(
        'native:centroids',
        {
            'INPUT': input_url,
            'ALL_PARTS': False,
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/origins.shp',
        },
    )


# P_m(d)
def sigmoid(b0, b1, b2, b3, d):
    """
    Sigmoid fuction for mode choice
    """
    d = float(d) / MAX_DISTANCE_M  # TODO: Check that this is the correct scaling
    try:
        S = 1 / (1 + math.exp(-(b0 + b1 * d + b2 * d ** 2 + b3 * math.sqrt(d))))
    except OverflowError:
        S = 'inf'
    return S


class timing(ContextDecorator):
    def __init__(self, msg: Optional[str] = None):
        self.msg = msg or 'execution'
        super().__init__()

    def __call__(self, *args, **kwargs):
        func = args[0]
        self.msg += f' ({func.__module__}.{func.__name__})'
        return super().__call__(*args, **kwargs)

    def __enter__(self):
        print(f'Timing {self.msg}...')
        self.ts = time()
        return self

    def __exit__(self, *exc):
        diff = time() - self.ts
        print(f'{self.msg} took: {diff:#1.2f} sec')
        return False
