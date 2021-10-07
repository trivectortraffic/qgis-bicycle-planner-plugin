import math
import numpy as np

from collections import defaultdict, namedtuple
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
from .utils import timing, sigmoid, print_mem

Origin = namedtuple('Origin', 'fid point pop')
Dest = namedtuple('Dest', 'fid point cat')
Route = namedtuple(
    'Route', 'origin_fid dest_fid cat distance decay p_bike p_ebike net_fids'
)


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
    # First strategy is for actual shortest distance calculation
    director.addStrategy(QgsNetworkDistanceStrategy())  # 0
    # Second strategy is a hack to be able to recover the edge id
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
    origin_i = dict(
        zip([origin.fid for origin in origins_data], range(len(origins_data)))
    )
    dest_map = dict(
        zip([dest.fid for dest in dests_data], tied_points[len(origins_data) :])
    )
    dest_i = dict(zip([dest.fid for dest in dests_data], range(len(dests_data))))

    d_ij = np.zeros((len(origin_i), len(dest_i)))

    print(d_ij.shape)

    dest_cat = {dest.fid: dest.cat for dest in dests_data}

    step = 100.0 / len(od_data)
    with timing('calculate connecting routes'):
        routes = []
        for i, (origin_fid, dest_fids) in enumerate(od_data):
            origin_point = origin_map[origin_fid]
            # TODO: check for NullIsland point (0.0, 0.0) == not found on network
            origin_vertex_id = graph.findVertex(origin_point)

            print('.', end='')
            # Calculate the tree and cost using the distance strategy (#0)
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
                    cost[dest_vertex_id] <= MAX_DISTANCE_M
                    or MAX_DISTANCE_M <= 0  # TODO: enable skipping max distance
                ):
                    route_distance = cost[dest_vertex_id]
                    # route_points = [graph.vertex(dest_vertex_id).point()]
                    cur_vertex_id = dest_vertex_id
                    route_fids = []
                    # Iterate the graph from dest to origin saving the edges
                    while cur_vertex_id != origin_vertex_id:
                        cur_edge = graph.edge(tree[cur_vertex_id])
                        # Here we recover the edge id through strategy #1
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

                    decay = math.exp(-gravity_value * route_distance / 1000.0)
                    p_bike = sigmoid(*bike_params, route_distance)
                    p_ebike = sigmoid(*ebike_params, route_distance)

                    d_ij[origin_i[origin_fid], dest_i[dest_fid]] = route_distance

                    # TODO: use namedtuple or dataclass
                    routes.append(
                        Route(
                            origin_fid,
                            dest_fid,
                            category,
                            route_distance,
                            decay,
                            p_bike,
                            p_ebike,
                            route_fids,
                        )
                    )
            feedback.setProgress(i * step)

        print()

    with timing('numpy'):
        N_j = len(dests_data)
        N_i = len(origins_data)

        print(d_ij, 'd_ij', d_ij.shape)

        D_j = np.ones(N_j)
        beta_j = np.array(
            [poi_gravity_values.get(dest.cat, np.nan) for dest in dests_data]
        )
        print(beta_j, 'beta_j', beta_j.shape)
        decay_ij = np.exp(-beta_j * d_ij / 1000.0)
        print(decay_ij, 'decay_ij', decay_ij.shape)
        decay_ij[np.isnan(decay_ij)] = 0
        print(decay_ij, 'decay_ij', decay_ij.shape)
        A_i = 1 / (D_j * decay_ij).sum(axis=1)
        print(A_i, 'A_i', A_i.shape)
        O_i = np.array([origin.pop for origin in origins_data])
        print(O_i, 'O_i', O_i.shape)

        T_ij = (
            (A_i * O_i)[:, None] * D_j * decay_ij
        )  # A_i O_i D_j f(d_ij), A_i = 1 / sum D_j f(d_ij)
        print(T_ij, 'T_ij', T_ij.shape)

    tmp_decay_ij = np.zeros(N_i * N_j).reshape(N_i, N_j)
    for route in routes:
        i = route.origin_fid - 1
        j = route.dest_fid - 1
        tmp_decay_ij[i, j] = route.decay
    print(tmp_decay_ij)

    with timing('post process routes'):
        pop = {origin.fid: origin.pop for origin in origins_data}
        decay_sums = {cat: defaultdict(float) for cat in poi_categories}
        bike_values = {cat: defaultdict(float) for cat in poi_categories}
        ebike_values = {cat: defaultdict(float) for cat in poi_categories}

        for route in routes:
            decay_sums[route.cat][route.origin_fid] += route.decay
        for route in routes:
            decay_sum = decay_sums[route.cat][route.origin_fid]
            bike_value = pop[route.origin_fid] * route.p_bike * route.decay / decay_sum
            ebike_value = (
                pop[route.origin_fid] * route.p_ebike * route.decay / decay_sum
            )
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


def vectorize(net_layer, origin_layer, dest_layer, origin_size_field, dest_size_field):
    net_ids = net_layer.allFeatureIds()

    crs = net_layer.crs()

    net = QgsVectorLayer(f'LineString?crs={crs.toWkt()}', 'network', 'memory')

    with timing('new net layer'), edit(net):
        for i, feature in enumerate(net_layer.getFeatures()):
            new = QgsFeature(i)
            new.setGeometry(feature.geometry())
            net.addFeature(new, flags=QgsFeatureSink.FastInsert)
            new.setId(i)
            net.updateFeature(new)

    for feature in net.getFeatures():
        print(feature.id())
        break

    print(min(net_ids), max(net_ids), len(net_ids))

    director = QgsVectorLayerDirector(
        source=net_layer,
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
    builder = QgsGraphBuilder(net_layer.crs())

    ## prepare points
    points = [origin.geometry().asPoint() for origin in origin_layer.getFeatures()] + [
        dest.geometry().asPoint() for dest in dest_layer.getFeatures()
    ]

    feedback = None
    if feedback is None:
        feedback = QgsProcessingFeedback()

        def progress(p):
            if int(10 * p % 100) == 0:
                print(f'{int(p):#3d}%')

        feedback.progressChanged.connect(progress)

    with timing('build network graph'):
        tied_points = director.makeGraph(builder, points, feedback=feedback)
        graph = builder.graph()


def get_fields():
    fields = QgsFields()
    fields.append(QgsField('network_fid', QVariant.Int))
    for cat in poi_categories:
        bike_field = f'{cat}_bike_value'
        ebike_field = f'{cat}_ebike_value'
        fields.append(QgsField(bike_field, QVariant.Double))
        fields.append(QgsField(ebike_field, QVariant.Double))
    return fields
