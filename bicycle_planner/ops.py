import math

from collections import defaultdict
from typing import List

from qgis import processing
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
    QgsProcessing,
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
    origin_data: list,
    destination_data: list,
    od_data: list,
    use_dest_fids: list,
    max_distance: int,
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

    crs = network_layer.crs()

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
    points = [origin[1] for origin in origin_data] + [
        dest[1] for dest in destination_data
    ]

    feedback = QgsProcessingFeedback()

    def progress(p):
        if int(10 * p % 100) == 0:
            print(f'{int(p):#3d}%')

    feedback.progressChanged.connect(progress)

    with timing('build network graph'):
        tied_points = director.makeGraph(builder, points, feedback=feedback)
        graph = builder.graph()

    origin_map = dict(
        zip([origin[0] for origin in origin_data], tied_points[: len(origin_data)])
    )
    dest_map = dict(
        zip([dest[0] for dest in destination_data], tied_points[len(origin_data) :])
    )

    with timing('calculate connecting routes'):
        routes = []
        for origin_fid, dest_fids in od_data:
            origin_point = origin_map[origin_fid]
            # TODO: check for NullIsland point (0.0, 0.0) == not found on network
            origin_vertex_id = graph.findVertex(origin_point)

            print('.', end='')
            (tree, cost) = QgsGraphAnalyzer.dijkstra(graph, origin_vertex_id, 0)

            for dest_fid in dest_fids:
                if dest_fid not in use_dest_fids:
                    # TODO: fix multi category
                    continue
                dest_point = dest_map[dest_fid]
                dest_vertex_id = graph.findVertex(dest_point)
                if tree[dest_vertex_id] != -1 and (
                    cost[dest_vertex_id] <= max_distance or max_distance <= 0
                ):
                    route_distance = cost[dest_vertex_id]
                    # route_points = [graph.vertex(dest_vertex_id).point()]
                    cur_vertex_id = dest_vertex_id
                    route_fids = []
                    # Iterate the graph
                    while cur_vertex_id != origin_vertex_id:
                        cur_edge = graph.edge(tree[cur_vertex_id])
                        route_fids.append(cur_edge.cost(1))
                        cur_vertex_id = cur_edge.fromVertex()
                        # route_points.append(graph.vertex(cur_vertex_id).point())

                    # route_points.reverse()
                    # route_geom = QgsGeometry.fromPolylineXY(route_points))

                    # Hack to remove duplicate fids
                    route_fids = list(
                        dict.fromkeys(route_fids)
                    )  # NOTE: requires python >= 3.7 for ordered dict FIXME: add python version check
                    route_fids.reverse()

                    # Calc
                    # TODO: Move to matrix and vectorize calculation using numpy
                    exp = math.exp(gravity_value * route_distance / 1000.0)
                    fbike = sigmoid(*bike_params, route_distance)
                    febike = sigmoid(*ebike_params, route_distance)

                    # TODO: use namedtuple or dataclass
                    routes.append(
                        (
                            origin_fid,
                            dest_fid,
                            route_distance,
                            exp,
                            fbike,
                            febike,
                            route_fids,
                        )
                    )

        print()

    pop = {k: v for k, _, v in origin_data}
    exp_sum = defaultdict(float)
    net_bike_values = defaultdict(float)
    net_ebike_values = defaultdict(float)

    with timing('post process routes'):
        for route in routes:
            exp_sum[route[0]] += route[3]
        for route in routes:
            bike_value = pop[route[0]] * route[4] * route[3] / exp_sum[route[0]]
            ebike_value = pop[route[0]] * route[5] * route[3] / exp_sum[route[0]]
            for fid in route[6]:
                net_bike_values[fid] += bike_value
                net_ebike_values[fid] += ebike_value

    output_layer = network_layer.clone()
    with timing('create result network'):
        with edit(output_layer):
            output_layer.addAttribute(QgsField('bike_value', QVariant.Double))
            output_layer.addAttribute(QgsField('ebike_value', QVariant.Double))

            output_layer.selectByIds(list(net_bike_values.keys()))
            for feature in output_layer.selectedFeatures():
                feature['bike_value'] = net_bike_values[feature.id()]
                feature['ebike_value'] = net_ebike_values[feature.id()]

                output_layer.updateFeature(feature)
            output_layer.removeSelection()

    return output_layer
