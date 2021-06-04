from functools import wraps
from time import time

from qgis import processing
from qgis.core import QgsVectorLayer


def ensure_singlepart(input_url: str) -> QgsVectorLayer:
    return processing.run(
        'native:multiparttosingleparts',
        dict(
            INPUT=input_url,
            OUTPUT='memory',
        ),
    )['OUTPUT']


def make_deso_centroids(input_url: str) -> QgsVectorLayer:
    processing.run(
        'native:centroids',
        {
            'INPUT': input_url,
            'ALL_PARTS': False,
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/origins.shp',
        },
    )


def timing(func):
    @wraps(func)
    def decorate(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        end = time()
        diff = end - start
        print(f'{func.__module__}.{func.__name__} took {diff:#3.2f} sec')
        return result

    return decorate
