import math

from collections import defaultdict, namedtuple
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
    QgsSpatialIndex,
    QgsFields,
    QgsFeatureStore,
    QgsFeatureSink,
    QgsWkbTypes,
)
from PyQt5.QtCore import QVariant

from .params import (
    poi_class_map,
    poi_categories,
    poi_gravity_values,
    mode_params_bike,
    mode_params_ebike,
)
from .utils import timing, sigmoid

Origin = namedtuple('Origin', 'fid point pop')
Dest = namedtuple('Dest', 'fid point cat')
Route = namedtuple(
    'Route', 'origin_fid dest_fid cat distance exp fbike febike net_fids'
)


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
def prepare_od_data(
    origins_source,
    dests_source,
    pop_field: str,
    class_field: str,
    max_distance: int = 25000,
):
    origins_data = [
        Origin(feature.id(), feature.geometry().asPoint(), feature[pop_field])
        for feature in origins_source.getFeatures()
    ]

    dests_data = [
        Dest(
            feature.id(),
            feature.geometry().asPoint(),
            poi_class_map.get(feature[class_field]),
        )
        for feature in dests_source.getFeatures()
    ]

    dests_sidx = QgsSpatialIndex(dests_source)
    od_data = []
    for feature in origins_source.getFeatures():
        point = feature.geometry().asPoint()
        od_data.append(
            (
                feature.id(),
                dests_sidx.nearestNeighbor(
                    point, neighbors=9001, maxDistance=max_distance
                ),  # FIXME: no hardcoded values
            )
        )

    return origins_data, dests_data, od_data


@timing()
def generate_od_routes(
    network_layer: QgsVectorLayer,
    origins_data: list,
    dests_data: list,
    od_data: list,
    max_distance: int = 30000,
    return_layer: bool = True,
    feedback: QgsProcessingFeedback = None,
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

    if not network_layer.wkbType() & QgsWkbTypes.LineString:
        raise Exception('Network layer must be of type LineString')
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
    points = [origin.point for origin in origins_data] + [
        dest.point for dest in dests_data
    ]

    if feedback is None:
        feedback = QgsProcessingFeedback()

        def progress(p):
            if int(10 * p % 100) == 0:
                print(f'{int(p):#3d}%')

        feedback.progressChanged.connect(progress)

    with timing('build network graph'):
        tied_points = director.makeGraph(builder, points, feedback=feedback)
        graph = builder.graph()

    origin_map = dict(
        zip([origin.fid for origin in origins_data], tied_points[: len(origins_data)])
    )
    dest_map = dict(
        zip([dest.fid for dest in dests_data], tied_points[len(origins_data) :])
    )
    dest_cat = {dest.fid: dest.cat for dest in dests_data}

    step = 100.0 / len(od_data)
    with timing('calculate connecting routes'):
        routes = []
        for i, (origin_fid, dest_fids) in enumerate(od_data):
            origin_point = origin_map[origin_fid]
            # TODO: check for NullIsland point (0.0, 0.0) == not found on network
            origin_vertex_id = graph.findVertex(origin_point)

            print('.', end='')
            (tree, cost) = QgsGraphAnalyzer.dijkstra(graph, origin_vertex_id, 0)
            print(':', end='')

            for dest_fid in dest_fids:
                if feedback.isCanceled():
                    return
                category = dest_cat[dest_fid]
                if category is None:
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
                    gravity_value = poi_gravity_values[category]
                    bike_params = mode_params_bike[category]
                    ebike_params = mode_params_ebike[category]

                    exp = math.exp(gravity_value * route_distance / 1000.0)
                    fbike = sigmoid(*bike_params, route_distance)
                    febike = sigmoid(*ebike_params, route_distance)

                    # TODO: use namedtuple or dataclass
                    routes.append(
                        Route(
                            origin_fid,
                            dest_fid,
                            category,
                            route_distance,
                            exp,
                            fbike,
                            febike,
                            route_fids,
                        )
                    )
            feedback.setProgress(i * step)

        print()

    with timing('post process routes'):
        pop = {origin.fid: origin.pop for origin in origins_data}
        exp_sums = {cat: defaultdict(float) for cat in poi_categories}
        bike_values = {cat: defaultdict(float) for cat in poi_categories}
        ebike_values = {cat: defaultdict(float) for cat in poi_categories}

        for route in routes:
            exp_sums[route.cat][route.origin_fid] += route.exp
        for route in routes:
            exp_sum = exp_sums[route.cat][route.origin_fid]
            bike_value = pop[route.origin_fid] * route.fbike * route.exp / exp_sum
            ebike_value = pop[route.origin_fid] * route.febike * route.exp / exp_sum
            for fid in route.net_fids:
                bike_values[route.cat][fid] += bike_value
                ebike_values[route.cat][fid] += ebike_value

    # FIXME: Un-kludge this
    with timing('create result features'):
        fields = get_fields()

        segments = []
        for feature in network_layer.getFeatures():
            fid = feature.id()
            segment = QgsFeature(fields)
            segment.setGeometry(QgsGeometry(feature.geometry()))

            segment['network_fid'] = fid
            for cat in poi_categories:
                bike_field = f'{cat}_bike_value'
                ebike_field = f'{cat}_ebike_value'

                segment[bike_field] = bike_values[cat].get(fid)
                segment[ebike_field] = ebike_values[cat].get(fid)

            segments.append(segment)

    if not return_layer:
        return segments

    with timing('create result layer'):
        output_layer = QgsVectorLayer(
            f'LineString?crs={crs.toWkt()}', 'segments', 'memory'
        )
        with edit(output_layer):
            for field in fields:
                output_layer.addAttribute(field)
            output_layer.addFeatures(segments, flags=QgsFeatureSink.FastInsert)

    return output_layer


def get_fields():
    fields = QgsFields()
    fields.append(QgsField('network_fid', QVariant.Int))
    for cat in poi_categories:
        bike_field = f'{cat}_bike_value'
        ebike_field = f'{cat}_ebike_value'
        fields.append(QgsField(bike_field, QVariant.Double))
        fields.append(QgsField(ebike_field, QVariant.Double))
    return fields
