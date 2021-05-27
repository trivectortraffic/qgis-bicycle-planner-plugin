# This Python Script aims to calculate the relation matrices based on Euclidean distances under 20km
# Different matrices are created for origins, destinations, and for each type of job from the SCB dataset

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
import processing
from datetime import datetime

origins = QgsVectorLayer("/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/Centroids_A3.shp")
destinations = QgsVectorLayer("/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/Centroids_A5.shp")

L = origins.fields().names()
print(L)

# Loop on the different types of jobs, SNI_01 to SNI_15
for i in range (2,17):
    id_list = []
    print(datetime.now())
    # Creation of a list of the ids where the field is over 0
    field = L[i]
    for f in origins.getFeatures():
        if f[field]>0:
            id_list.append(f.id())
    print(len(id_list))
    
    # Creation of layers containting only the non-null features for the fields
    origins.selectByIds([k for k in id_list])
    destinations.selectByIds([k for k in id_list])
    O='/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/O'+str(i)+'.shp'
    D='/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/D'+str(i)+'.shp'
    writer_o = QgsVectorFileWriter.writeAsVectorFormat(origins,O,"utf-8",origins.crs(),"ESRI Shapefile",onlySelected=True)
    writer_d = QgsVectorFileWriter.writeAsVectorFormat(destinations,D,"utf-8",origins.crs(),"ESRI Shapefile",onlySelected=True)
    
    # Processing the algorithm SAGA point distances for these created layers
    processing.run("saga:pointdistances", {'POINTS':O,'ID_POINTS':'Ruta','NEAR':D,'ID_NEAR':'Ruta','FORMAT':1,'MAX_DIST':20000,'DISTANCES':'/Users/laurentcazor/Documents/Trivector work/Work destination choice/QGIS/OD'+str(i)+'.dbf'})