from contextlib import ContextDecorator
from time import time
from typing import Optional


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
