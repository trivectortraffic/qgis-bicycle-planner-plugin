from datetime import datetime

from qgis.analysis import (
    QgsNetworkDistanceStrategy,
    QgsVectorLayerDirector,
    QgsGraphBuilder,
    QgsGraphAnalyzer,
)
from qgis.core import (
    QgsField,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingFeedback,
    QgsFeature,
    QgsVectorFileWriter,
)
from PyQt5.QtCore import QVariant


def shortest_path(
    iface,
    network_url,
    points_url,
    relations_url,
    origin_id,
    destination_id,
    name,
    max_d,
    out_crs,
):
    """
    Shortest path algorithm based on Dijkstra's algorithm
    """

    LINEID = 'Distance'
    POINTID1 = 'FromFID'
    POINTID2 = 'ToFid'
    FromToID = 'FromToFID'

    access_layer = iface.addVectorLayer(points_url, "Points", "ogr")
    amenities_layer = iface.addVectorLayer(points_url, "Points", "ogr")
    network_layer = iface.addVectorLayer(network_url, "Network", "ogr")
    relations_layer = iface.addVectorLayer(relations_url, "Relations", "ogr")

    # Skapa ett resultatslager (Från Astrids kod)
    crs = network_layer.crs().toWkt()
    outLayer = QgsVectorLayer('Linestring?crs=' + crs, 'Paths_' + name, 'memory')
    outdp = outLayer.dataProvider()

    # add the two point ID field
    outdp.addAttributes(
        [
            QgsField(LINEID, QVariant.Int),
            QgsField(POINTID1, QVariant.Int),
            QgsField(POINTID2, QVariant.Int),
            QgsField(FromToID, QVariant.String),
        ]
    )
    outLayer.updateFields()

    distance = max_d

    ## prepare graph
    vl = network_layer
    strategy = QgsNetworkDistanceStrategy()
    director = QgsVectorLayerDirector(
        vl, -1, '', '', '', QgsVectorLayerDirector.DirectionBoth
    )
    director.addStrategy(strategy)
    crs = vl.crs()
    builder = QgsGraphBuilder(network_layer.crs())

    ## prepare points
    access_features = access_layer.getFeatures()
    access_count = access_layer.featureCount()
    amenities_features = amenities_layer.getFeatures()
    amenities_count = amenities_layer.featureCount()
    access_count + amenities_count
    relations_layer.featureCount()
    points = []
    ids = []

    for f in access_features:
        points.append(f.geometry().asPoint())
        ids.append(f['ID'])
    for f in amenities_features:
        points.append(f.geometry().asPoint())
        ids.append(f['ID'])

    feedback = QgsProcessingFeedback()

    def progress(p):
        if int(10 * p % 100) == 0:
            print(f'{int(p):#3d}%')

    feedback.progressChanged.connect(progress)

    print("start graph build", datetime.now())
    tiedPoints = director.makeGraph(builder, points, feedback=feedback)
    graph = builder.graph()
    print("end graph build", datetime.now())

    a = 0

    start = datetime.now()
    print('Starting cost calculation')
    for feature in relations_layer.getFeatures():

        # count percentage done and no features
        a = a + 1

        if a == 1:
            old_point_id = feature[destination_id]

        # if a/15000==int(a/15000):
        # print (int((a/relations_count)*100),'%')

        point_id = feature[origin_id]
        near_id = feature[destination_id]

        point_id = int(point_id)
        near_id = int(near_id)

        from_point = tiedPoints[point_id]
        to_point = tiedPoints[near_id]
        from_id = graph.findVertex(from_point)
        to_id = graph.findVertex(to_point)
        if point_id != old_point_id:
            (tree, cost) = QgsGraphAnalyzer.dijkstra(graph, from_id, 0)

        if tree[to_id] != -1 and (cost[to_id] <= distance or distance <= 0):
            costToPoint = cost[to_id]
            # print(costToPoint)
            route = [graph.vertex(to_id).point()]
            curPos = to_id
            # Iterate the graph
            while curPos != from_id:
                curPos = graph.edge(tree[curPos]).fromVertex()
                route.insert(0, graph.vertex(curPos).point())
            connector = QgsFeature(outLayer.fields())
            connector.setGeometry(QgsGeometry.fromPolylineXY(route))
            # print(curPos, type(curPos))

            connector.setAttribute(0, costToPoint)
            connector.setAttribute(1, feature[origin_id])
            connector.setAttribute(2, feature[destination_id])
            connector.setAttribute(
                3, str(feature[origin_id]) + '-' + str(feature[destination_id])
            )
            outdp.addFeatures([connector])

        old_point_id = point_id

    elapsed = datetime.now() - start
    print(f'Finished in {elapsed}')

    Output = '/tmp/Paths_' + name + '.shp'
    err, msg = QgsVectorFileWriter.writeAsVectorFormat(
        outLayer, Output, "utf-8", out_crs, "ESRI Shapefile"
    )
    print(err, msg)
    iface.addVectorLayer(Output, '', 'ogr')

    print("end", datetime.now())
