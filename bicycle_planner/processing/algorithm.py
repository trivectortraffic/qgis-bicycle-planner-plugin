from qgis import processing

from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsSpatialIndex,
    QgsGeometry,
    QgsMultiLineString,
    QgsWkbTypes,
    QgsProcessingParameterVectorDestination,
    QgsVectorLayer,
    QgsProcessingParameterFile,
)
from PyQt5.QtCore import QVariant


from ..ops import get_fields, generate_od_routes
from ..utils import make_single, make_centroids


class FlowAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    NETWORK = 'NETWORK'
    ORIGINS = 'ORIGINS'
    DESTS = 'DESTINATIONS'
    WORK = 'WORK'

    SOCIO_FILE = 'SOCIO_FILE'

    POP_FIELD = 'POPULATION_FIELD'
    WORK_FIELD = 'WORK_FIELD'
    CLASS_FIELD = 'CLASS_FIELD'

    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.NETWORK,
                self.tr('Network layer'),
                [QgsProcessing.TypeVectorLine],
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ORIGINS,
                self.tr('Origins layer'),
                [QgsProcessing.TypeVectorAnyGeometry],
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.POP_FIELD,
                self.tr('Population field'),
                defaultValue='totalt',
                parentLayerParameterName=self.ORIGINS,
                optional=False,
                type=QgsProcessingParameterField.Numeric,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.DESTS,
                self.tr('Destinations layer'),
                [QgsProcessing.TypeVectorAnyGeometry],
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.CLASS_FIELD,
                self.tr('Destination class field'),
                defaultValue='fclass',
                parentLayerParameterName=self.DESTS,
                optional=False,
                type=QgsProcessingParameterField.String,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.WORK,
                self.tr('Work places layer'),
                [QgsProcessing.TypeVectorAnyGeometry],
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.WORK_FIELD,
                self.tr('Size of workplace field'),
                defaultValue='Totalt',
                parentLayerParameterName=self.WORK,
                optional=False,
                type=QgsProcessingParameterField.Numeric,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.SOCIO_FILE,
                self.tr('Socio-economic data'),
                optional=True,
                extension='csv',
                # help='Comma separated must have a header where the first value is the join value on origins and the second column contains socio economic index values',
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature origins_source and sink. The 'sink_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        network_source = self.parameterAsVectorLayer(parameters, self.NETWORK, context)
        origins_source = self.parameterAsVectorLayer(parameters, self.ORIGINS, context)
        dests_source = self.parameterAsVectorLayer(parameters, self.DESTS, context)
        work_source = self.parameterAsVectorLayer(parameters, self.WORK, context)

        pop_field = self.parameterAsString(parameters, self.POP_FIELD, context)
        class_field = self.parameterAsString(parameters, self.CLASS_FIELD, context)
        work_field = self.parameterAsString(parameters, self.WORK_FIELD, context)

        network_layer = make_single(
            network_source,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        origins_layer = make_centroids(
            make_single(
                origins_source,
                context=context,
                feedback=feedback,
                is_child_algorithm=True,
            ),
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        work_layer = make_centroids(
            make_single(
                work_source,
                context=context,
                feedback=feedback,
                is_child_algorithm=True,
            ),
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        dests_layer = make_single(
            dests_source,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        features = generate_od_routes(
            network_layer=network_layer,
            origin_layer=origins_layer,
            poi_layer=dests_layer,
            work_layer=work_layer,
            work_size_field=work_field,
            size_field=pop_field,
            class_field=class_field,
            return_layer=False,
            feedback=feedback,
        )

        (sink, sink_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            features[0].fields(),
            network_layer.wkbType(),
            network_layer.sourceCrs(),
        )

        step = 100.0 / len(features)
        for i, feature in enumerate(features):
            if feedback.isCanceled():
                break
            r = sink.addFeature(feature, QgsFeatureSink.FastInsert)
            if not r:
                print(feature, [(value, type(value)) for value in feature.attributes()])
                break
            feedback.setProgress(i * step)

        return {self.OUTPUT: sink_id}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'createnetwork'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Generate bicycle flow network')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Vector processing')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'vector'

    def tr(self, string):
        return string  # QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return FlowAlgorithm()


class NvdbAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    NETWORK = 'NETWORK'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.NETWORK,
                self.tr('Network layer'),
                [QgsProcessing.TypeVectorLine],
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature origins_source and sink. The 'sink_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        network_source = self.parameterAsVectorLayer(parameters, self.NETWORK, context)

        rlid_field = None
        from_field = None
        to_field = None
        class_field = None
        oper_field = None
        speedf_field = None
        speedb_field = None
        adt_field = None
        type_field = None

        for field in network_source.fields():
            name = field.name()
            lname = name.lower()

            if lname == 'route_id':
                rlid_field = name
            elif lname == 'from_measure':
                from_field = name
            elif lname == 'to_measure':
                to_field = name
            elif lname == 'klass_181':
                class_field = name
            elif lname == 'vagha_6':
                oper_field = name
            elif lname == 'f_hogst_225':
                speedf_field = name
            elif lname == 'b_hogst_225':
                speedb_field = name
            elif lname == 'adt_f_117':
                adt_field = name
            elif lname == 'vagtr_474':
                type_field = name

        expr = f'"{type_field}" = 2'
        if not network_source.setSubsetString(expr):
            raise Exception('Failed to set subset')

        result = processing.run(
            'native:buffer',
            {
                'INPUT': network_source,
                #'DISSOLVE': True,
                'DISTANCE': 100,
                'END_CAP_STYLE': 2,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )['OUTPUT']

        buffer_layer = context.takeResultLayer(result)

        print(len(buffer_layer))
        bike_buffer = buffer_layer.getGeometry(1)
        print(bike_buffer)

        index = QgsSpatialIndex(buffer_layer.getFeatures(), feedback=feedback)
        geoms = {f.id(): f.geometry() for f in buffer_layer.getFeatures()}

        ids = index.intersects(bike_buffer.boundingBox())
        print(ids)
        for i in ids:
            if bike_buffer.intersects(geometry=geoms[i]):
                print('BOOOOM!')

        fields = QgsFields()
        fields.append(QgsField('rlid', QVariant.String))
        fields.append(QgsField('from_measure', QVariant.Double))
        fields.append(QgsField('to_measure', QVariant.Double))
        fields.append(QgsField('oper', QVariant.Int))
        fields.append(QgsField('class', QVariant.Int))
        fields.append(QgsField('speed', QVariant.Int))
        fields.append(QgsField('adt', QVariant.Int))

        fields.append(QgsField('rec', QVariant.Int))
        fields.append(QgsField('lts', QVariant.Int))
        fields.append(QgsField('ratio', QVariant.Double))
        ratios = {1: 0, 2: 1, 3: 1.58, 4: 2}

        fields.append(QgsField('gc', QVariant.Bool))

        expr = (
            f'"{type_field}" = 1 AND "{oper_field}" IN (1, 2) AND "{class_field}" <= 5'
        )
        print(expr)
        if not network_source.setSubsetString(expr):
            raise Exception('Failed to set subset')

        network_layer = make_single(
            network_source,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        if not network_source.setSubsetString(''):
            raise Exception('Failed to set subset')

        (sink, sink_id) = self.parameterAsSink(
            parameters,
            name=self.OUTPUT,
            context=context,
            fields=fields,
            geometryType=network_layer.wkbType(),
            crs=network_layer.sourceCrs(),
        )

        n = len(network_layer)
        chunk = n // 100
        print(n, chunk)
        for i, feat in enumerate(network_layer.getFeatures()):
            """if not feat[type_field] == 1:
                continue
            if not feat[oper_field] in [1, 2]:
                continue
            if feat[class_field] > 5:
                continue"""

            geom = feat.geometry()

            _feat = QgsFeature(fields)
            _feat.setGeometry(geom)
            _feat['rlid'] = feat[rlid_field]
            _feat['from_measure'] = feat[from_field]
            _feat['to_measure'] = feat[to_field]

            _feat['speed'] = speed = max(feat[speedf_field], feat[speedb_field])
            _feat['adt'] = adt = feat[adt_field]
            _feat['class'] = clss = feat[class_field]
            _feat['oper'] = oper = feat[oper_field]

            # Find existing bike infra
            gc = False
            for fid in index.intersects(geom.boundingBox()):
                if geom.intersects(geometry=geoms[fid]):
                    gc = True
                    break

            _feat['gc'] = gc

            if not adt:
                if clss <= 3:
                    adt = 9001
                elif clss == 4:
                    adt = 3000
                else:
                    adt = 900

            if not speed:
                speed = 70

            # VGU classify required infra
            rec = None
            if clss <= 2:
                rec = 5
            elif speed <= 30:
                rec = 1
            elif speed <= 60 and adt <= 2000:
                rec = 2
            elif speed <= 80 and adt <= 4000 or speed <= 40 and adt > 4000:
                rec = 3
            elif speed > 80 or adt > 4000:
                rec = 4

            # Debug missing
            if not adt:
                rec = -1
            if not speed:
                rec = -2

            _feat['rec'] = rec

            # LTS
            lts = None
            if clss <= 2 or speed > 80 or (adt > 4000 and speed > 40 and not gc):
                lts = 4
            elif speed <= 30 or (adt <= 1000 and speed <= 40):
                lts = 1
            elif gc and (
                adt <= 1000
                or (speed <= 60 and adt <= 2000)
                or (speed <= 40 and adt <= 4000)
            ):
                lts = 1
            elif gc and speed > 60 and adt > 4000:
                lts = 3
            elif not gc and (
                adt > 4000
                or (speed > 40 and adt >= 2000)
                or (speed > 60 and adt >= 1000)
            ):
                lts = 3
            else:
                lts = 2

            _feat['lts'] = lts
            _feat['ratio'] = ratios[lts]

            # Done
            sink.addFeature(_feat)

            if feedback and i % chunk == 0:
                p = 100 * i / n
                feedback.setProgress(p)

        return {self.OUTPUT: sink_id}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'classifynvdb'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Classify NVDB network')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Vector processing')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'vector'

    def tr(self, string):
        return string  # QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return NvdbAlgorithm()
