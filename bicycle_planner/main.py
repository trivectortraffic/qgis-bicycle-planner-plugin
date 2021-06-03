import os.path

from qgis.core import QgsApplication, QgsMessageLog
from qgis.gui import QgisInterface
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dialog import Dialog
from .processing import Provider


class Plugin:
    def __init__(self, iface: QgisInterface) -> None:
        print('__init__')
        self.iface = iface
        self.first_start = True
        self.initProcessing()

    def initProcessing(self) -> None:
        print('initProvider')
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self) -> None:
        print('initGui')
        """self.toolButton = QToolButton()
        self.toolButton.setMenu(QMenu())
        self.toolButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.toolBtnAction = self.iface.addToolBarWidget(self.toolButton)

        self.actionRun = QAction(
            QIcon(os.path.join(os.path.dirname(__file__), "icon.png")),
            'Bicycle Planner',
            self.iface.mainWindow(),
        )
        self.actionRun.setToolTip('Bicycle Planner')
        self.actionRun.setText('Bicycle Planner')
        self.iface.addPluginToMenu('&Bicyle Planner', self.actionRun)"""
        # create action that will start plugin configuration
        self.action = QAction(
            QIcon(os.path.join(os.path.dirname(__file__), 'icon.png')),
            "Bicycle Planner",
            self.iface.mainWindow(),
        )
        self.action.setObjectName("testAction")
        self.action.setWhatsThis("Configuration for test plugin")
        self.action.setStatusTip("This is status tip")
        self.action.triggered.connect(self.run)

        # add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Bicycle Planner", self.action)

        # connect to signal renderComplete which is emitted when canvas
        # rendering is done
        self.iface.mapCanvas().renderComplete.connect(self.renderTest)

    def unload(self):
        """for action in [
            self.actionRun,
        ]:
            self.iface.removePluginMenu('&Bicyle Planner', action)
            self.iface.removeToolBarIcon(action)
            self.iface.unregisterMainWindowAction(action)

        self.iface.removeToolBarIcon(self.toolBtnAction)"""
        # remove the plugin menu item and icon
        self.iface.removePluginMenu("&Bicycle Planner", self.action)
        self.iface.removeToolBarIcon(self.action)

        # disconnect form signal of the canvas
        self.iface.mapCanvas().renderComplete.disconnect(self.renderTest)

        QgsApplication.processingRegistry().removeProvider(self.provider)

    def run(self):
        print("BicyclePlanner: run called!")
        QgsMessageLog.logMessage('Fooooooo')

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start:
            self.first_start = False
            self.dlg = Dialog()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def renderTest(self, painter):
        # use painter for drawing to map canvas
        print("TestPlugin: renderTest called!")


def classFactory(iface: QgisInterface) -> Plugin:
    print('classFactory')
    return Plugin(iface)
