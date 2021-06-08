import math

from datetime import datetime
from typing import List

from qgis.analysis import (
    QgsNetworkDistanceStrategy,
    QgsVectorLayerDirector,
    QgsGraphBuilder,
    QgsGraphAnalyzer,
    QgsNetworkStrategy,
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

from .utils import timing, sigmoid


class SaveFidStrategy(QgsNetworkStrategy):
    """
    Strategy class to save the underlyging network link feature ids. The QGIS
    graph builder does not save information about the network used to build
    the routing graph. This class is a hack to enable mapping route_points paths back
    onto the network by querying the cost of each edge. The edge object returns
    the fid of the network.
    """

    def cost(self, distance: float, feature: QgsFeature) -> int:
        try:
            return int(feature.id())
        except ValueError:
            # TODO: log trace, make sure to do it in a thread safe way
            return -1


@timing()
def generate_od_routes(
    network_layer: QgsVectorLayer,
    points_layer: QgsVectorLayer,
    relations_data: QgsVectorLayer,
    origin_field: QgsVectorLayer,
    destination_field: QgsVectorLayer,
    max_distance: int,
    crs: QgsCoordinateReferenceSystem,
    gravity_value: float,
    bike_params: List[float],
    ebike_params: List[float],
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
    NETWORK_ID_FIELD = 'network_fids'
    FROM_ID_FIELD = 'bp_from_id'
    TO_ID_FIELD = 'bp_to_id'
    FROM_TO_FIELD = 'id'

    EXP_FIELD = 'exp'
    BIKE_P_FIELD = 'fbike'
    EBIKE_P_FIELD = 'febike'

    # Create empty output layer
    output_layer = QgsVectorLayer(f'linestring?crs={crs.toWkt()}', 'Graph', 'memory')

    # Add attribute fields
    with edit(output_layer):
        output_layer.addAttribute(QgsField(DISTANCE_FIELD, QVariant.Double))
        output_layer.addAttribute(QgsField(NETWORK_ID_FIELD, QVariant.String))
        output_layer.addAttribute(QgsField(FROM_ID_FIELD, QVariant.Int))
        output_layer.addAttribute(QgsField(TO_ID_FIELD, QVariant.Int))
        output_layer.addAttribute(QgsField(FROM_TO_FIELD, QVariant.String))

        output_layer.addAttribute(QgsField(EXP_FIELD, QVariant.Double))
        output_layer.addAttribute(QgsField(BIKE_P_FIELD, QVariant.Double))
        output_layer.addAttribute(QgsField(EBIKE_P_FIELD, QVariant.Double))

    ## prepare graph
    director = QgsVectorLayerDirector(
        source=network_layer,
        directionFieldId=-1,
        directDirectionValue='',
        reverseDirectionValue='',
        bothDirectionValue='',
        defaultDirection=QgsVectorLayerDirector.DirectionBoth,
    )
    director.addStrategy(QgsNetworkDistanceStrategy())  # 0
    director.addStrategy(SaveFidStrategy())  # 1
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
    prev_point_id = -1
    with timing('calculate connecting routes'), edit(output_layer):
        for i, feature in enumerate(relations_data.getFeatures()):
            from_point_id = int(feature[origin_field])
            to_point_id = int(feature[destination_field])

            from_point = point_id_map[from_point_id]
            to_point = point_id_map[to_point_id]
            # TODO: check for NullIsland point (0.0, 0.0) == not found on network
            from_vertex_id = graph.findVertex(from_point)
            to_vertex_id = graph.findVertex(to_point)

            # New start point => new tree
            if from_point_id != prev_point_id:
                # print(f'building dijkstra tree for {from_point_id}')
                print('.', end='')
                (tree, cost) = QgsGraphAnalyzer.dijkstra(graph, from_vertex_id, 0)

            if tree[to_vertex_id] != -1 and (
                cost[to_vertex_id] <= max_distance or max_distance <= 0
            ):
                route_distance = cost[to_vertex_id]
                # print(route_distance)
                route_points = [graph.vertex(to_vertex_id).point()]
                cur_vertex_id = to_vertex_id
                route_fids = []
                # Iterate the graph
                while cur_vertex_id != from_vertex_id:
                    cur_edge = graph.edge(tree[cur_vertex_id])
                    route_fids.append(cur_edge.cost(1))
                    cur_vertex_id = cur_edge.fromVertex()
                    route_points.append(graph.vertex(cur_vertex_id).point())

                # route_points.reverse()
                route_fids = list(
                    dict.fromkeys(route_fids)
                )  # NOTE: requires python >= 3.7 for ordered dict FIXME: add python version check
                route_fids.reverse()

                connector = QgsFeature(output_layer.fields())
                connector.setGeometry(QgsGeometry.fromPolylineXY(route_points))
                connector[DISTANCE_FIELD] = route_distance
                connector[NETWORK_ID_FIELD] = ', '.join(
                    map(str, route_fids)
                )  # FIXME: temporary solution, skip layer creation completely and retunr dict with values
                connector[FROM_ID_FIELD] = from_point_id
                connector[TO_ID_FIELD] = to_point_id
                connector[FROM_TO_FIELD] = f'{from_point_id}-{to_point_id}'

                # Calc
                # TODO: Move to matrix and vectorize calculation
                exp = math.exp(gravity_value * route_distance / 1000.0)
                fbike = sigmoid(*bike_params, route_distance)
                febike = sigmoid(*ebike_params, route_distance)

                connector[EXP_FIELD] = exp
                connector[BIKE_P_FIELD] = fbike
                connector[EBIKE_P_FIELD] = febike

                output_layer.addFeature(connector)

            prev_point_id = from_point_id

            # progress(100.0 * i / n)
        print()

    return output_layer
