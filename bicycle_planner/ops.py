import math

from collections import defaultdict, namedtuple
from time import time
from typing import List

from devtools import debug
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
    MAX_DISTANCE_M,
    poi_class_map,
    poi_categories,
    poi_gravity_values,
    mode_params_bike,
    mode_params_ebike,
)
from .utils import timing, sigmoid


MAX_NEIGHBORS = 9001

Route = namedtuple('Route', 'i j cat distance decay p_bike p_ebike net_fids')


class SaveFidStrategy(QgsNetworkStrategy):
    """
    Strategy class to save the underlying network link feature ids. The QGIS
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
    origins_source,
    dests_source,
    size_field: str,
    class_field: str,
    max_distance: int = 25000,
    return_layer: bool = True,
    return_raw: bool = False,
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
    # First strategy is for actual shortest distance calculation
    director.addStrategy(QgsNetworkDistanceStrategy())  # 0
    # Second strategy is a hack to be able to recover the edge id
    director.addStrategy(SaveFidStrategy())  # 1
    builder = QgsGraphBuilder(crs)

    ## spatial index

    dest_sidx = QgsSpatialIndex(dests_source)

    ## prepare points
    orig_n = len(origins_source)
    dest_n = len(dests_source)

    orig_points = [None] * orig_n
    orig_sizes = [None] * orig_n
    dest_points = [None] * dest_n
    dest_sizes = [None] * dest_n
    dest_fids = [None] * dest_n
    dest_cats = [None] * dest_n

    for i, feat in enumerate(origins_source.getFeatures()):
        orig_points[i] = feat.geometry().asPoint()
        orig_sizes[i] = feat[size_field]

    for i, feat in enumerate(dests_source.getFeatures()):
        dest_points[i] = feat.geometry().asPoint()
        dest_fids[i] = feat.id()
        dest_sizes[i] = 1  # TODO: dest size
        dest_cats[i] = poi_class_map.get(feat[class_field])

    # points = [origin.point for origin in origins_data] + [
    #    dest.point for dest in dests_data
    # ]

    if feedback is None:
        feedback = QgsProcessingFeedback()

        def progress(p):
            if int(10 * p % 100) == 0:
                print(f'{int(p):#3d}%')

        feedback.progressChanged.connect(progress)

    with timing('build network graph'):
        tied_points = director.makeGraph(
            builder, orig_points + dest_points, feedback=feedback
        )
        graph = builder.graph()

    orig_tied_points = tied_points[:orig_n]
    dest_tied_points = tied_points[orig_n:]

    dest_fid_to_tied_points = dict(zip(dest_fids, enumerate(dest_tied_points)))

    orig_dests = [None] * orig_n
    for i, point in enumerate(orig_points):
        orig_dests[i] = [
            dest_fid_to_tied_points[fid]
            for fid in dest_sidx.nearestNeighbor(
                point, neighbors=MAX_NEIGHBORS, maxDistance=max_distance
            )
        ]

    step = 100.0 / orig_n
    time_dijkstra = 0.0
    time_route = 0.0
    with timing('calculate connecting routes'):
        routes = []
        # for i, (origin_fid, dest_fids) in enumerate(od_data):
        for i, (orig_point, dests) in enumerate(zip(orig_tied_points, orig_dests)):
            origin_vertex_id = graph.findVertex(orig_point)

            # Calculate the tree and cost using the distance strategy (#0)
            ts = time()
            (tree, cost) = QgsGraphAnalyzer.dijkstra(graph, origin_vertex_id, 0)
            time_dijkstra += time() - ts

            for j, dest_point in dests:
                if feedback.isCanceled():
                    return
                category = dest_cats[j]
                if category is None:
                    continue
                dest_vertex_id = graph.findVertex(dest_point)
                if tree[dest_vertex_id] != -1 and (
                    cost[dest_vertex_id] <= MAX_DISTANCE_M
                    or MAX_DISTANCE_M <= 0  # TODO: enable skipping max distance
                ):
                    route_distance = cost[dest_vertex_id]
                    # route_points = [graph.vertex(dest_vertex_id).point()]
                    cur_vertex_id = dest_vertex_id
                    route_fids = []
                    # Iterate the graph from dest to origin saving the edges
                    ts = time()
                    while cur_vertex_id != origin_vertex_id:
                        cur_edge = graph.edge(tree[cur_vertex_id])
                        # Here we recover the edge id through strategy #1
                        route_fids.append(cur_edge.cost(1))
                        cur_vertex_id = cur_edge.fromVertex()
                        # route_points.append(graph.vertex(cur_vertex_id).point())
                    time_route += time() - ts

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

                    # NOTE: we include dest size in decay here
                    decay = dest_sizes[j] * math.exp(
                        gravity_value * route_distance / 1000.0
                    )
                    p_bike = sigmoid(*bike_params, route_distance)
                    p_ebike = sigmoid(*ebike_params, route_distance)

                    # TODO: use namedtuple or dataclass
                    routes.append(
                        Route(
                            i,
                            j,
                            category,
                            route_distance,
                            decay,
                            p_bike,
                            p_ebike,
                            route_fids,
                        )
                    )
            feedback.setProgress(i * step)

        print(f'dijkstra took: {time_dijkstra:#1.2f} sec')
        print(f'route took: {time_route:#1.2f} sec')

    with timing('post process routes'):
        decay_sums = {cat: defaultdict(float) for cat in poi_categories}
        bike_values = {cat: defaultdict(float) for cat in poi_categories}
        ebike_values = {cat: defaultdict(float) for cat in poi_categories}

        for route in routes:
            # NOTE: dest size is included in decay
            decay_sums[route.cat][route.i] += route.decay
        for route in routes:
            decay_sum = decay_sums[route.cat][route.i]
            bike_value = orig_sizes[route.i] * route.p_bike * route.decay / decay_sum
            ebike_value = orig_sizes[route.i] * route.p_ebike * route.decay / decay_sum
            for fid in route.net_fids:
                bike_values[route.cat][fid] += bike_value
                ebike_values[route.cat][fid] += ebike_value

    if return_raw:
        return bike_values, ebike_values

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
