import math

from bokeh.layouts import column, row

import libcasm.xtal as xtal

from ._ViewAtomicStructure import (
    ViewAtomicStructure,
)
from ._ViewControl import (
    ViewControl,
)


class ProjectionView:
    def __init__(
        self,
        view_control: ViewControl,
    ):
        self.view_control = view_control
        component_params = self.view_control.component_params

        self.view_xz = ViewAtomicStructure(
            doc=None,
            component_params=component_params,
            v1=[1.0, 0.0, 0.0],
            v2=[0.0, 0.0, 1.0],
        )

        self.view_yz = ViewAtomicStructure(
            doc=None,
            component_params=component_params,
            v1=[0.0, 1.0, 0.0],
            v2=[0.0, 0.0, 1.0],
        )

        self.view_xy = ViewAtomicStructure(
            doc=None,
            component_params=component_params,
            v1=[1.0, 0.0, 0.0],
            v2=[0.0, 1.0, 0.0],
        )

        self.view_cabinet = ViewAtomicStructure(
            doc=None,
            component_params=component_params,
            cabinet=(0.2, math.pi / 6.0),
        )

    def set_structure(
        self,
        structure: xtal.Structure,
        name: str,
    ):
        self.view_xz.set_structure(
            structure=structure,
            title="X-Z plane view",
            new_marker_size_scale=self.view_control.marker_size_scale,
            new_marker_alpha_scale=self.view_control.marker_alpha_scale,
        )
        self.view_yz.set_structure(
            structure=structure,
            title="Y-Z plane view",
            new_marker_size_scale=self.view_control.marker_size_scale,
            new_marker_alpha_scale=self.view_control.marker_alpha_scale,
        )
        self.view_xy.set_structure(
            structure=structure,
            title="X-Y plane view",
            new_marker_size_scale=self.view_control.marker_size_scale,
            new_marker_alpha_scale=self.view_control.marker_alpha_scale,
        )
        self.view_cabinet.set_structure(
            structure=structure,
            title=name,
            new_marker_size_scale=self.view_control.marker_size_scale,
            new_marker_alpha_scale=self.view_control.marker_alpha_scale,
            new_cabinet=(
                self.view_control.cabinet_scale,
                self.view_control.cabinet_angle,
            ),
        )
        self.view_cabinet.update_view_basis(
            v1=self.view_control.cabinet_v1,
            v2=self.view_control.cabinet_v2,
        )

    def make_layout(
        self,
    ):
        p_xz = self.view_xz.make_plot()
        p_xz.xaxis.axis_label = "x"
        p_xz.yaxis.axis_label = "z"

        p_yz = self.view_yz.make_plot()
        p_yz.xaxis.axis_label = "y"
        p_yz.yaxis.axis_label = "z"

        p_xy = self.view_xy.make_plot()
        p_xy.xaxis.axis_label = "x"
        p_xy.yaxis.axis_label = "y"

        p_cabinet = self.view_cabinet.make_plot()
        p_cabinet.xaxis.axis_label = "b1 (cabinet)"
        p_cabinet.yaxis.axis_label = "b2 (cabinet)"

        return column(
            row(p_xy, p_cabinet),
            row(p_xz, p_yz),
        )
