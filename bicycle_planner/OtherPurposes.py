# This code aims to do all the layer pre-processing (i.e. before calculating the shortest paths)
# Its input are the network, the DeSO (origins) and the OSM POI (destinations)

# Shortest path algorithm based on Dijkstra's algorithm
# from Shortest_Path import Shortest_Path
import time
from datetime import datetime

from qgis import processing
from qgis.analysis import (
    QgsNetworkDistanceStrategy,
    QgsVectorLayerDirector,
    QgsGraphBuilder,
    QgsGraphAnalyzer,
)
from qgis.core import (
    edit,
    QgsField,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingFeedback,
    QgsFeature,
    QgsVectorFileWriter,
)
from PyQt5.QtCore import QVariant


##### Shortest path function, not designed to stay in this file but I had some struggles
def Shortest_Path(
    network_url, points_url, relations_url, origin_id, destination_id, name, max_d
):

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

    Output = (
        '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/Paths_'
        + name
        + '.shp'
    )
    QgsVectorFileWriter.writeAsVectorFormat(
        outLayer, Output, "utf-8", layer_poi.crs(), "ESRI Shapefile"
    )
    iface.addVectorLayer(Output, '', 'ogr')

    print("end", datetime.now())


##### End of Shortest path function #####


def main():
    ## To test the program, we chose a small test area ##
    deso = '/Users/laurentcazor/Documents/Trivector work/Data/Befolkning_2013_2018_shp__12f99f76-aa2f-40a9-a23b-06f3f08a10bf_/B1DesoSW_20181231/B1DeSO_SW_region.shp'

    ### First part: prepare data for the shortest path calculations, run the shortest path algorithm ###
    # 0. Make sure we have single parts

    processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/small_poi.shp',
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/small_poi_s.shp',
        },
    )
    processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/small_net.shp',
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/small_net_s.shp',
        },
    )

    poi = '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/small_poi_s.shp'
    network = '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/small_net_s.shp'

    # 1. Creation of centroids for DeSO

    processing.run(
        "native:centroids",
        {
            'INPUT': deso,
            'ALL_PARTS': False,
            'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/origins.shp',
        },
    )
    origins = '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/origins.shp'

    # 2. OSM data: separation by purpose
    # Creation of a new attribute

    leisure = [
        'attraction',
        'cinema',
        'community_centre',
        'dog_park',
        'garden_centre',
        'golf_course',
        'museum',
        'park',
        'picnic_site',
        'pitch',
        'playground',
        'sports_centre',
        'theatre',
        'track',
    ]
    shopping = [
        'bicycle_shop',
        'clothes',
        'gift_shop',
        'mobile_phone_shop',
        'outdoor_shop',
        'supermarket',
        'toy_shop',
        'video_shop',
    ]
    services = [
        'atm',
        'bank',
        'bakery',
        'cafe',
        'car_dealership',
        'car_wash',
        'car_rental',
        'dentist',
        'fast_food',
        'hairdresser',
        'kindergarten',
        'kiosk',
        'laundry',
        'library',
        'pharmacy',
        'police',
        'post_box',
        'post_office',
        'pub',
        'recycling',
        'recycling_paper',
        'restaurant',
        'school',
        'toilet',
        'town_hall',
        'veterinary',
    ]
    touring = [
        'artwork',
        'chalet',
        'castle',
        'camp_site',
        'fountain',
        'hostel',
        'hotel',
        'ruins',
        'tourist_info',
        'tower',
        'viewpoint',
    ]

    layer_poi = iface.addVectorLayer(poi, '', 'ogr')
    layer_p = layer_poi.dataProvider()
    layer_p.addAttributes([QgsField('Purpose', QVariant.String)])
    layer_poi.updateFields()

    id_leis = []
    id_shop = []
    id_serv = []
    id_tour = []

    with edit(layer_poi):
        for f in layer_poi.getFeatures():
            if f["fclass"] in leisure:
                f['Purpose'] = 'Leisure'
                id_leis.append(f.id())
            elif f["fclass"] in shopping:
                f['Purpose'] = 'Shopping'
                id_shop.append(f.id())
            elif f["fclass"] in services:
                f['Purpose'] = 'Services'
                id_serv.append(f.id())
            elif f["fclass"] in touring:
                f['Purpose'] = 'Touring'
                id_tour.append(f.id())
            layer_poi.updateFeature(f)

    # 3. Creation of the point layers with a unique ID

    # 3.1 Unique ID for DeSO

    layer_origins = iface.addVectorLayer(origins, '', 'ogr')
    layer_origins.dataProvider().addAttributes([QgsField('ID', QVariant.Int)])
    layer_origins.updateFields()

    with edit(layer_origins):
        for f in layer_origins.getFeatures():
            f['ID'] = 1 + f.id()
            layer_origins.updateFeature(f)

    X = layer_origins.featureCount()

    # 3.2 Creation of Unique ID for all the destinations

    purp = [id_leis, id_shop, id_serv, id_tour]
    purp_name = ['Leisure', 'Shopping', 'Services', 'Touring']

    # Sub layer for each purpose
    for i in range(len(purp)):
        p = purp[i]
        name = purp_name[i]
        layer_poi.selectByIds([k for k in p])
        dest_p = (
            '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/small_poi'
            + name
            + '.shp'
        )
        writer = QgsVectorFileWriter.writeAsVectorFormat(
            layer_poi,
            dest_p,
            "utf-8",
            layer_poi.crs(),
            "ESRI Shapefile",
            onlySelected=True,
        )

        L = iface.addVectorLayer(dest_p, '', 'ogr')
        L.dataProvider().addAttributes([QgsField('ID', QVariant.Int)])
        L.updateFields()
        with edit(L):
            for f in L.getFeatures():
                f['ID'] = 1 + X + f.id()
                L.updateFeature(f)

        # 3.3 Merge layers
        processing.run(
            "native:union",
            {
                'INPUT': dest_p,
                'OVERLAY': origins,
                'OVERLAY_FIELDS_PREFIX': 'D_',
                'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/OD_'
                + name
                + '.shp',
            },
        )
        OD_p = iface.addVectorLayer(
            '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/OD_'
            + name
            + '.shp',
            '',
            'ogr',
        )
        with edit(OD_p):
            for f in OD_p.getFeatures():
                f['ID'] = max(f['ID'], f['D_ID'])
                OD_p.updateFeature(f)

        # 4. Creation of a relation layer: origins and destinations which are not too far

        processing.run(
            "saga:pointdistances",
            {
                'POINTS': origins,
                'ID_POINTS': 'ID',
                'NEAR': dest_p,
                'ID_NEAR': 'ID',
                'FORMAT': 1,
                'MAX_DIST': 25000,
                'DISTANCES': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/Relations_'
                + name
                + '.dbf',
            },
        )
        relations = (
            '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/Relations_'
            + name
            + '.dbf'
        )

        # 5. Run the shortest path algorithm
        processing.run(
            "native:multiparttosingleparts",
            {
                'INPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/OD_'
                + name
                + '.shp',
                'OUTPUT': '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/OD_s_'
                + name
                + '.shp',
            },
        )
        points = (
            '/Users/laurentcazor/Documents/Trivector work/Work destination choice/Test_small/OD_s_'
            + name
            + '.shp'
        )
        Shortest_Path(
            network, points, relations, 'ID_POINT', 'ID_NEAR', purp_name[i], 30000
        )

    ### Second part: give weights to the shortest paths calculated: see code OtherPurposes_2.py ###


if __name__ == '__main__':
    main()
