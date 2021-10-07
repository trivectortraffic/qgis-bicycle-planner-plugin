import os.path
import sys
from pytest import fixture

pytest_plugins = ('pytest_qgis',)


@fixture
def datadir(pytestconfig):
    rootdir = pytestconfig.rootdir
    return os.path.join(rootdir, 'tests', 'data')
