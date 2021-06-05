from datetime import datetime

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
    QgsCoordinateReferenceSystem,
)
from PyQt5.QtCore import QVariant

from .utils import timing


@timing()
def shortest_path(
    network_layer: QgsVectorLayer,
    points_layer: QgsVectorLayer,
    relations_data: QgsVectorLayer,
    origin_field: QgsVectorLayer,
    destination_field: QgsVectorLayer,
    max_distance: int,
    crs: QgsCoordinateReferenceSystem,
) -> QgsVectorLayer:
    """
    Shortest path algorithm based on Dijkstra's algorithm

    :param network_layer: road network
    :param points_layer: combined from to points
    :param relations_data: tabular from to id data
    :param origin_field: name of from field
    :param destination_field: name of to field
    :param max_distance: maximum distance/cost
    :param crs: output layer crs
    """

    DISTANCE_FIELD = 'bp_distance'
    FROM_ID_FIELD = 'bp_from_id'
    TO_ID_FIELD = 'bp_to_id'
    FROM_TO_FIELD = 'id'

    # Create empty output layer
    output_layer = QgsVectorLayer(f'linestring?crs={crs.toWkt()}', 'Graph', 'memory')

    # Add attribute fields
    with edit(output_layer):
        output_layer.addAttribute(QgsField(DISTANCE_FIELD, QVariant.Double))
        output_layer.addAttribute(QgsField(FROM_ID_FIELD, QVariant.Int))
        output_layer.addAttribute(QgsField(TO_ID_FIELD, QVariant.Int))
        output_layer.addAttribute(QgsField(FROM_TO_FIELD, QVariant.String))

    ## prepare graph
    strategy = QgsNetworkDistanceStrategy()
    director = QgsVectorLayerDirector(
        source=network_layer,
        directionFieldId=-1,
        directDirectionValue='',
        reverseDirectionValue='',
        bothDirectionValue='',
        defaultDirection=QgsVectorLayerDirector.DirectionBoth,
    )
    director.addStrategy(strategy)
    builder = QgsGraphBuilder(crs)

    ## prepare points
    data = [
        (feature['point_id'], feature.geometry().asPoint())
        for feature in points_layer.getFeatures()
    ]
    points = [v[1] for v in data]
    point_ids = [v[0] for v in data]

    feedback = QgsProcessingFeedback()

    def progress(p):
        if int(10 * p % 100) == 0:
            print(f'{int(p):#3d}%')

    feedback.progressChanged.connect(progress)

    with timing('build network graph'):
        tied_points = director.makeGraph(builder, points, feedback=feedback)
        graph = builder.graph()

    point_id_map = dict(zip(point_ids, tied_points))

    n = relations_data.featureCount()
    prev_point_id = None
    with timing('calculate connecting routes'), edit(output_layer):
        for i, feature in enumerate(relations_data.getFeatures()):
            if prev_point_id is None:
                prev_point_id = feature[destination_field]

            point_id = int(feature[origin_field])
            near_id = int(feature[destination_field])

            from_point = point_id_map[point_id]
            to_point = point_id_map[near_id]
            # TODO: check for NullIsland point (0.0, 0.0) == not found on network
            from_vertex_id = graph.findVertex(from_point)
            to_vertex_id = graph.findVertex(to_point)

            # New start point => new tree
            if point_id != prev_point_id:
                print(f'building dijkstra tree for {point_id}')
                (tree, cost) = QgsGraphAnalyzer.dijkstra(graph, from_vertex_id, 0)

            if tree[to_vertex_id] != -1 and (
                cost[to_vertex_id] <= max_distance or max_distance <= 0
            ):
                route_cost = cost[to_vertex_id]
                # print(route_cost)
                route = [graph.vertex(to_vertex_id).point()]
                cur_vertex_id = to_vertex_id
                # Iterate the graph
                while cur_vertex_id != from_vertex_id:
                    cur_vertex_id = graph.edge(tree[cur_vertex_id]).fromVertex()
                    route.append(graph.vertex(cur_vertex_id).point())
                route.reverse()

                connector = QgsFeature(output_layer.fields())
                connector.setGeometry(QgsGeometry.fromPolylineXY(route))
                connector[DISTANCE_FIELD] = route_cost
                connector[FROM_ID_FIELD] = point_id
                connector[TO_ID_FIELD] = near_id
                connector[FROM_TO_FIELD] = f'{point_id}-{near_id}'
                output_layer.addFeature(connector)

            prev_point_id = point_id

            progress(100.0 * i / n)
            if i > n / 40:
                break

    return output_layer
