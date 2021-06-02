import os.path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .algorithm import Algorithm


class Provider(QgsProcessingProvider):
    def __init__(self):
        """
        Default constructor.
        """
        print('provider __init__')
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        print('provider loadAlgo')
        self.addAlgorithm(Algorithm())
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'bicycle-planner'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return 'Bicycle Planner Generator'

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        print('provider icon')
        return QIcon(
            os.path.join(os.path.split(os.path.dirname(__file__))[0], 'icon.png')
        )  # QgsProcessingProvider.icon(self)

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
