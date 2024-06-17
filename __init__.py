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

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load LineDensityAnalysis class from file LineDensityAnalysis.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .line_density_analysis import LineDensityAnalysisPlugin
    return LineDensityAnalysisPlugin(iface)
