import os.path
import sys
from pytest import fixture

pytest_plugins = ('pytest_qgis',)


@fixture
def datadir(pytestconfig):
    rootdir = pytestconfig.rootdir
    return os.path.join(rootdir, 'tests', 'data')


@fixture(autouse=True, scope='session')
def qgis_processing(qgis_app):
    python_plugins_path = os.path.join(qgis_app.pkgDataPath(), 'python', 'plugins')
    if python_plugins_path not in sys.path:
        sys.path.append(python_plugins_path)
    from processing.core.Processing import Processing

    Processing.initialize()
