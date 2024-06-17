# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Fast Line Density Analysis
                                 A QGIS plugin
 A fast line density visualization plugin for geospatial analytics
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
__author__ = 'LDV Group'
__date__ = '2024-06-01'
__copyright__ = '(C) 2024 by LDV Group'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import math
import os

import numpy as np
import pandas
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsMessageLog,
    Qgis,
    QgsProject,
    QgsRasterLayer,
    QgsStyle
)
import re
from qgis.PyQt.QtGui import QIcon
from .ldv import ldv
from .rasterstyle import applyPseudocolor
import pandas as pd
from osgeo import gdal
from datetime import datetime
import time

MESSAGE_CATEGORY = 'Fast Line Density Analysis'


class LDVAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    STARTPOINT = 'STARTPOINT'
    ENDPOINT = 'ENDPOINT'
    WIDTH = 'WIDTH'
    HEIGHT = 'HEIGHT'
    SPATIALBANDWIDTH = 'SPATIALBANDWIDTH'
    RELATIVEERROR = 'RELATIVEERROR'
    RAMPNAME = 'RAMPNAME'
    INVERT = 'INVERT'
    INTERPOLATION = 'INTERPOLATION'
    MODE = 'MODE'
    CLASSES = 'CLASSES'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Input CSV file'),
                [QgsProcessing.TypeFile]
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.STARTPOINT,
                self.tr('Start point'),
                None,
                self.INPUT
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.ENDPOINT,
                self.tr('End point'),
                None,
                self.INPUT
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.WIDTH,
                'Width',
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=320, optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.HEIGHT,
                'Height',
                type=QgsProcessingParameterNumber.Integer,
                minValue=0,
                defaultValue=240,
                optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SPATIALBANDWIDTH,
                'Spatial bandwidth(meters)',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                defaultValue=1000,
                optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RELATIVEERROR,
                'Relative error',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                defaultValue=0.1,
                optional=False
            )
        )
        if Qgis.QGIS_VERSION_INT >= 32200:
            param = QgsProcessingParameterString(
                self.RAMPNAME,
                'Select color ramp',
                defaultValue='Turbo',
                optional=False
            )
            param.setMetadata(
                {
                    'widget_wrapper': {
                        'value_hints': QgsStyle.defaultStyle().colorRampNames()
                    }
                }
            )
        else:
            param = QgsProcessingParameterEnum(
                self.RAMPNAME,
                'Select color ramp',
                options=QgsStyle.defaultStyle().colorRampNames(),
                defaultValue=0,
                optional=False
            )
        self.addParameter(param)
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INVERT,
                'Invert color ramp',
                False,
                optional=False)
        )
        # Chose Kernel shape
        # param = QgsProcessingParameterEnum('KERNEL', 'Kernel shape',
        #                                    options=['Quartic', 'Triangular', 'Uniform', 'Triweight', 'Epanechnikov'],
        #                                    defaultValue=0, optional=False)
        # param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        # self.addParameter(param)
        # param = QgsProcessingParameterNumber('DECAY', 'Decay ratio (Triangular kernels only)',
        #                                      type=QgsProcessingParameterNumber.Double, defaultValue=0, minValue=-100,
        #                                      maxValue=100, optional=False)
        # param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        # self.addParameter(param)

        param = QgsProcessingParameterEnum(
            self.INTERPOLATION,
            'Interpolation',
            options=['Discrete', 'Linear', 'Exact'],
            defaultValue=1,
            optional=False)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterEnum(
            self.MODE,
            'Mode',
            options=['Continuous', 'Equal Interval', 'Quantile'],
            defaultValue=2,
            optional=False)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(
            self.CLASSES,
            'Number of gradient colors',
            QgsProcessingParameterNumber.Integer,
            defaultValue=10,
            minValue=5,
            optional=False)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

        # Output
        # self.addParameter(
        #     QgsProcessingParameterRasterDestination(self.OUTPUT, 'Output KDV heatmap',
        #                                             createByDefault=True, defaultValue=None)
        # )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        lyr = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        csv_file = self.parameterAsFile(parameters, self.INPUT, context)
        start_field = self.parameterAsString(parameters, self.STARTPOINT, context)
        end_field = self.parameterAsString(parameters, self.ENDPOINT, context)
        row_pixels = self.parameterAsInt(parameters, self.WIDTH, context)
        col_pixels = self.parameterAsInt(parameters, self.HEIGHT, context)
        bandwidth_s = self.parameterAsDouble(parameters, self.SPATIALBANDWIDTH, context)
        epsilon = self.parameterAsDouble(parameters, self.RELATIVEERROR, context)


        if Qgis.QGIS_VERSION_INT >= 32200:
            ramp_name = self.parameterAsString(parameters, self.RAMPNAME, context)
        else:
            ramp_name = self.parameterAsEnum(parameters, self.RAMPNAME, context)
        invert = self.parameterAsBool(parameters, self.INVERT, context)
        interp = self.parameterAsInt(parameters, self.INTERPOLATION, context)
        mode = self.parameterAsInt(parameters, self.MODE, context)
        num_classes = self.parameterAsInt(parameters, self.CLASSES, context)
        rlayer = processLDV(csv_file, start_field, end_field, row_pixels, col_pixels, bandwidth_s, epsilon,ramp_name, invert, interp, mode,
                            num_classes, feedback)

        return {self.OUTPUT: rlayer}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'linedensityvisualization(LDV)'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Line density visualization (LDV)")

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return LDVAlgorithm()

    def helpUrl(self):
        return "https://github.com/libkdv/libkdv"

    def shortDescription(self):
        return "Efficient and accurate line density visualization."

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icons/ldv.png'))

def processLDV(csv_file, start_field, end_field, row_pixels, col_pixels, bandwidth_s, epsilon, ramp_name, invert, interp, mode, num_classes,
               feedback):
    # Get currentTime
    currentTime =datetime.now()
    # toString
    timeStr = currentTime.strftime('%Y-%m-%d %H-%M-%S')
    # Current project path
    prjPath = QgsProject.instance().homePath()
    savePath = prjPath + "/temp/LDV/" + timeStr
    # Create save directory
    try:
        os.makedirs(savePath)
    except FileExistsError:
        pass
    except Exception as e:
        feedback.pushInfo('Create diectory failed, error:{}'.format(e))
        # QgsMessageLog.logMessage("Create diectory failed, error:{}".format(e), MESSAGE_CATEGORY, level=Qgis.Info)
    # Start LDV
    ldv_data = ldv(csv_file, start_field, end_field, row_pixels, col_pixels, bandwidth_s, epsilon, prjPath, feedback)
    result = ldv_data.compute()
    if feedback.isCanceled():
        return {}
    # End LDV

    # Start generate LDV raster layer
    # feedback.pushInfo('Start generate LDV raster layer')
    # start = time.time()
    result.rename(columns={"lon": "x", "lat": "y", "val": "value"}, inplace=True)
    # Sorted according to first y minus then x increasing (from top left corner, top to bottom left to right)
    result_sorted = result.sort_values(by=["y", "x"], ascending=[False, True])
    path = savePath + "/LDV_Result"
    result_sorted.to_csv(path + ".xyz", index=False, header=False, sep=" ")
    demn = gdal.Translate(path + ".tif", path + ".xyz", outputSRS="EPSG:4326")
    demn = None
    os.remove(path + '.xyz')
    fn = path + '.tif'
    rlayer = QgsRasterLayer(fn, 'LDV_Result')
    end = time.time()
    # duration = end - start
    feedback.setProgress(100)
    # feedback.pushInfo('End generate LDV raster layer, duration:{}s'.format(duration))
    if feedback.isCanceled():
        return {}
    applyPseudocolor(rlayer, ramp_name, invert, interp, mode, num_classes, True)
    QgsProject.instance().addMapLayer(rlayer)
    return rlayer
