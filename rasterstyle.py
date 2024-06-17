from qgis.core import (
    QgsStyle,
    QgsRasterBandStats,
    QgsColorRampShader,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer
)
from qgis.PyQt.QtGui import QColor
def applyPseudocolor(layer, ramp_name, invert, interp, mode, num_classes, is_ldv):
    if interp == 0:  # Discrete
        interpolation = QgsColorRampShader.Discrete
    elif interp == 1:  # Liner Interpolated
        interpolation = QgsColorRampShader.Interpolated
    elif interp == 2:  # Exact
        interpolation = QgsColorRampShader.Exact

    if mode == 0:  # Continuous
        shader_mode = QgsColorRampShader.Continuous
    elif mode == 1:  # Equal Interval
        shader_mode = QgsColorRampShader.EqualInterval
    elif mode == 2:  # Quantile
        shader_mode = QgsColorRampShader.Quantile
    provider = layer.dataProvider()
    stats = provider.bandStatistics(1, QgsRasterBandStats.Min | QgsRasterBandStats.Max)

    style = QgsStyle.defaultStyle()
    ramp = style.colorRamp(ramp_name)
    if invert:
        ramp.invert()
    color_ramp = QgsColorRampShader(stats.minimumValue, stats.maximumValue, ramp, interpolation, shader_mode)
    if shader_mode == QgsColorRampShader.Quantile:
        color_ramp.classifyColorRamp(classes=num_classes, band=1, input=provider)
    else:
        color_ramp.classifyColorRamp(classes=num_classes)

    if is_ldv:
        if color_ramp.colorRampItemList():
            color_ramp_item_list = color_ramp.colorRampItemList()
            if color_ramp_item_list:
                first_item = color_ramp_item_list[0]
                first_item.color = QColor(0, 0, 0, 0)
                color_ramp.setColorRampItemList(color_ramp_item_list)

    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(color_ramp)

    # Create a new single band pseudocolor renderer
    renderer = QgsSingleBandPseudoColorRenderer(provider, layer.type(), raster_shader)

    layer.setRenderer(renderer)
    layer.renderer().setOpacity(0.75)
    layer.triggerRepaint()