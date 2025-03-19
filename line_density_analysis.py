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

import os
import sys
import inspect
from qgis.PyQt.QtWidgets import QMenu, QToolButton
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
from .line_density_analysis_provider import LineDensityAnalysisProvider
import processing
import logging

cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]

if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)


class LineDensityAnalysisPlugin(object):

    def __init__(self, iface):
        self.iface = iface
        self.provider = LineDensityAnalysisProvider()

    def initProcessing(self):
        """Init Processing provider for QGIS >= 3.8."""

        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.toolbar = self.iface.addToolBar('Fast Line Density Analysis Toolbar')
        self.toolbar.setObjectName('FastLineDensityAnalysisToolbar')
        self.toolbar.setToolTip('Fast Line Density Analysis Toolbar')

        # Create the KDV menu items
        menu = QMenu()

        icon = QIcon(os.path.join(os.path.dirname(__file__), 'icons/ldv.png'))
        self.ldvAction = menu.addAction(icon, 'Line density visualization', self.ldvAlgorithm)
        self.iface.addPluginToMenu("Fast line density analysis", self.ldvAction)

        # Add the KDV algorithms to the toolbar
        icon = QIcon(os.path.join(os.path.dirname(__file__), 'icons/ldv.png'))
        self.kdvsButton = QToolButton()
        self.kdvsButton.setMenu(menu)
        self.kdvsButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.kdvsButton.setDefaultAction(self.ldvAction)
        self.kdvsButton.setIcon(icon)
        self.kdvsToolbar = self.toolbar.addWidget(self.kdvsButton)

        self.initProcessing()

    def unload(self):
        try:
            if hasattr(self, 'ldvAction') and self.ldvAction:
                self.iface.removePluginMenu('Fast line density analysis', self.ldvAction)
                self.ldvAction = None
        except Exception as e:
            logging.error(f"Error removing plugin menu item: {e}")

        try:
            logging.debug('Removing toolbar icon')
            if hasattr(self, 'kdvsToolbar') and self.kdvsToolbar:
                self.iface.removeToolBarIcon(self.kdvsToolbar)
                self.kdvsToolbar = None
        except Exception as e:
            logging.error(f"Error removing toolbar icon: {e}")

        try:
            if hasattr(self, 'toolbar') and self.toolbar:
                self.iface.mainWindow().removeToolBar(self.toolbar)
                self.toolbar.deleteLater()
                self.toolbar = None
        except Exception as e:
            logging.error(f"Error deleting toolbar: {e}")

        try:
            logging.debug('Removing processing provider')
            if hasattr(self, 'provider') and self.provider:
                QgsApplication.processingRegistry().removeProvider(self.provider)
                self.provider = None
        except Exception as e:
            logging.error(f"Error removing processing provider: {e}")


    def ldvAlgorithm(self):
        processing.execAlgorithmDialog('linedensityanalysis:linedensityvisualization(LDV)', {})