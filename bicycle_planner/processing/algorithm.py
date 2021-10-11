from qgis import processing

from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsWkbTypes,
    QgsProcessingParameterVectorDestination,
    QgsVectorLayer,
    QgsProcessingParameterFile,
)

from ..ops import get_fields, generate_od_routes
from ..utils import make_single, make_centroids


class Algorithm(QgsProcessingAlgorithm):
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
        return Algorithm()
