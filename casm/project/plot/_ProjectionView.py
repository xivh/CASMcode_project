import bokeh.models
from bokeh.layouts import column, row

import libcasm.xtal as xtal

from ._DashboardStyles import DashboardStyles
from ._view import SinglePointProjection
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
        self.name = "(None)"
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

        self.projection_view = ViewAtomicStructure(
            doc=None,
            component_params=component_params,
            projection=SinglePointProjection(),
        )

        self.title_div = bokeh.models.Div(
            text=f"""<b>{self.name}</b>""",
            width=1200,
            height=50,  # Sufficient height for the text
            styles={
                "display": "flex",  # Make the Div a flex container
                # "justify-content": "center",  # Center content horizontally
                "align-items": "center",  # Center content vertically
                "font-size": "32px",  # Adjust font size
                "padding-bottom": "10px",  # Add some space below
                # 'border': '1px solid red' # Uncomment for debugging to see bounds
            },
        )

    def set_structure(
        self,
        structure: xtal.Structure,
        name: str,
    ):
        self.name = name
        self.title_div.text = f"""<b>{self.name}</b>"""
        self.view_xz.set_structure(
            structure=structure,
            title="X-Z plane view",
            new_marker_size_scale=self.view_control.marker_size_scale,
            new_marker_alpha_scale=self.view_control.marker_alpha_scale,
            new_component_params=self.view_control.component_params,
        )
        self.view_yz.set_structure(
            structure=structure,
            title="Y-Z plane view",
            new_marker_size_scale=self.view_control.marker_size_scale,
            new_marker_alpha_scale=self.view_control.marker_alpha_scale,
            new_component_params=self.view_control.component_params,
        )
        self.view_xy.set_structure(
            structure=structure,
            title="X-Y plane view",
            new_marker_size_scale=self.view_control.marker_size_scale,
            new_marker_alpha_scale=self.view_control.marker_alpha_scale,
            new_component_params=self.view_control.component_params,
        )
        self.projection_view.set_structure(
            structure=structure,
            title="Projection view",
            new_marker_size_scale=self.view_control.marker_size_scale,
            new_marker_alpha_scale=self.view_control.marker_alpha_scale,
            new_projection=self.view_control.projection,
            new_component_params=self.view_control.component_params,
        )
        self.projection_view.update_view_basis(
            v1=self.view_control.projection_v1,
            v2=self.view_control.projection_v2,
        )

    def make_layout(
        self,
        styles: DashboardStyles,
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

        p_projection = self.projection_view.make_plot()
        p_projection.xaxis.axis_label = "b1 (projection)"
        p_projection.yaxis.axis_label = "b2 (projection)"

        return column(
            self.title_div,
            row(p_xy, p_projection),
            row(p_xz, p_yz),
            margin=(0, 20),
        )
