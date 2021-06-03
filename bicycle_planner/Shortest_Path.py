# Shortest path algorithm as a function of several arguments

import time
from datetime import datetime

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *


def Shortest_Path(network_url, points_url, relations_url, max_d):

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
    outLayer = QgsVectorLayer('Linestring?crs=' + crs, 'connector_lines', 'memory')
    outdp = outLayer.dataProvider()

    # add the two point ID field
    outdp.addAttributes(
        [
            QgsField(LINEID, QVariant.String),
            QgsField(POINTID1, QVariant.String),
            QgsField(POINTID2, QVariant.String),
            QgsField(FromToID, QVariant.String),
        ]
    )
    outLayer.updateFields()

    distance = max_d
    QgsProcessingFeedback()

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

    print("start graph build", datetime.now())
    tiedPoints = director.makeGraph(builder, points)
    graph = builder.graph()
    print("end graph build", datetime.now())
    time.sleep(3)

    a = 0

    for feature in relations_layer.getFeatures():

        # count percentage done and no features
        a = a + 1

        if a == 1:
            old_point_id = feature["ID_2"]

        # if a/15000==int(a/15000):
        # print (int((a/relations_count)*100),'%')

        point_id = feature["ID"]
        near_id = feature["ID_2"]

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

            connector.setAttribute(0, str(costToPoint))
            connector.setAttribute(1, str(feature["ID"]))
            connector.setAttribute(2, str(feature["ID_2"]))
            connector.setAttribute(3, str(feature["ID"]) + '-' + str(feature["ID_2"]))
            outdp.addFeatures([connector])

        old_point_id = point_id

    QgsProject.instance().addMapLayer(outLayer)

    print("end", datetime.now())


network_url = '/Users/laurentcazor/Documents/Trivector work/Data/V_gkartan_2020_shp__e3424bf0-68a3-49f2-91e3-e9f45f401cd3_/vl_riks.shp'

for i in range(2, 5):

    points_url = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/UnionS_'
        + str(i)
        + '.shp'
    )
    final_relations = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/Relations_'
        + str(i)
        + '.gpkg|layername=Relations_'
        + str(i)
    )

    # Running of the shortest path algorithm
    Shortest_Path(network_url, points_url, final_relations, 25000)
