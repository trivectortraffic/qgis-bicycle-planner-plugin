# This code aims to do all the layer pre-processing (i.e. before calculating the shortest paths)
# Its input are the network, the DeSO (origins) and the OSM POI (destinations)

from qgis import processing
from qgis.core import (
    edit,
    QgsField,
    QgsVectorLayer,
    QgsVectorFileWriter,
)
from PyQt5.QtCore import QVariant

from .ops import shortest_path


def main(iface):
    ### First part: prepare data for the shortest path calculations, run the shortest path algorithm ###
    # 0. Make sure we have single parts
    processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': '/tmp/small_poi.shp',
            'OUTPUT': '/tmp/small_poi_s.shp',
        },
    )
    processing.run(
        "native:multiparttosingleparts",
        {
            'INPUT': '/tmp/small_net.shp',
            'OUTPUT': '/tmp/small_net_s.shp',
        },
    )

    # 1. Creation of centroids for DeSO
    # deso = '/Users/laurentcazor/Documents/Trivector work/Data/Befolkning_2013_2018_shp__12f99f76-aa2f-40a9-a23b-06f3f08a10bf_/B1DesoSW_20181231/B1DeSO_SW_region.shp'
    # processing.run(
    #    "native:centroids",
    #    {
    #        'INPUT': deso,
    #        'ALL_PARTS': False,
    #        'OUTPUT': '/tmp/origins.shp',
    #    },
    # )

    poi = '/tmp/small_poi_s.shp'
    network = '/tmp/small_net_s.shp'
    origins = '/tmp/origins.shp'

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
        dest_p = '/tmp/small_poi' + name + '.shp'
        err, msg = QgsVectorFileWriter.writeAsVectorFormat(
            layer_poi,
            dest_p,
            "utf-8",
            layer_poi.crs(),
            "ESRI Shapefile",
            onlySelected=True,
        )
        print(err, msg)

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
                'OUTPUT': '/tmp/OD_' + name + '.shp',
            },
        )
        OD_p = iface.addVectorLayer(
            '/tmp/OD_' + name + '.shp',
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
                'DISTANCES': '/tmp/Relations_' + name + '.dbf',
            },
        )
        relations = '/tmp/Relations_' + name + '.dbf'

        # 5. Run the shortest path algorithm
        processing.run(
            "native:multiparttosingleparts",
            {
                'INPUT': '/tmp/OD_' + name + '.shp',
                'OUTPUT': '/tmp/OD_s_' + name + '.shp',
            },
        )
        points = '/tmp/OD_s_' + name + '.shp'
        shortest_path(
            iface,
            network,
            points,
            relations,
            'ID_POINT',
            'ID_NEAR',
            purp_name[i],
            30000,
            layer_poi.crs(),
        )

    ### Second part: give weights to the shortest paths calculated: see code OtherPurposes_2.py ###


if __name__ == '__main__':

    class QgisInterface:
        """
        Fake QGIS Interface when running from terminal
        """

        def addVectorLayer(self, *args):
            return QgsVectorLayer(*args)

    main(QgisInterface())
