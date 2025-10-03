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

        self._layout = None
        self._styles = None

        self.update_layout_type()

        self.title_div = bokeh.models.Div(
            text=f"""<b>{self.name}</b>""",
            # width=1200,
            # height=50,  # Sufficient height for the text
            # styles={
            #     "display": "flex",  # Make the Div a flex container
            #     # "justify-content": "center",  # Center content horizontally
            #     "align-items": "center",  # Center content vertically
            #     "font-size": "32px",  # Adjust font size
            #     "padding-bottom": "10px",  # Add some space below
            #     # 'border': '1px solid red' # Uncomment for debugging to see bounds
            # },
            **self.view_control.title_params,
        )

    def update_layout_type(self):
        """Update the layout type and reinitialize views if layout type has changed.

        This method should be called whenever `layout_type` in view_control changes. It
        uses `layout_type`, `component_params`, `figure_params` from `view_control` to
        reinitialize the views accordingly.

        """
        component_params = self.view_control.component_params

        if self.view_control.layout_type == "multiview":

            figure_params = self.view_control.multiview_figure_params
            self.view_xz = ViewAtomicStructure(
                doc=None,
                component_params=component_params,
                v1=[1.0, 0.0, 0.0],
                v2=[0.0, 0.0, 1.0],
                figure_params=figure_params,
            )

            self.view_yz = ViewAtomicStructure(
                doc=None,
                component_params=component_params,
                v1=[0.0, 1.0, 0.0],
                v2=[0.0, 0.0, 1.0],
                figure_params=figure_params,
            )

            self.view_xy = ViewAtomicStructure(
                doc=None,
                component_params=component_params,
                v1=[1.0, 0.0, 0.0],
                v2=[0.0, 1.0, 0.0],
                figure_params=figure_params,
            )
            self.projection_view = ViewAtomicStructure(
                doc=None,
                component_params=component_params,
                projection=SinglePointProjection(),
                figure_params=figure_params,
            )
        elif self.view_control.layout_type == "singleview":

            figure_params = self.view_control.singleview_figure_params

            self.view_xz = None
            self.view_yz = None
            self.view_xy = None
            self.projection_view = ViewAtomicStructure(
                doc=None,
                component_params=component_params,
                projection=SinglePointProjection(),
                figure_params=figure_params,
            )
        else:
            raise ValueError(f"Invalid layout type: {self.view_control.layout_type}")

    def set_structure(
        self,
        structure: xtal.Structure,
        name: str,
    ):
        self.name = name
        self.title_div.text = f"""<b>{self.name}</b>"""

        if self.view_control.layout_type == "multiview":
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
        elif self.view_control.layout_type != "singleview":
            raise ValueError(f"Invalid layout type: {self.view_control.layout_type}")

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
        self._styles = styles

        if self.view_control.layout_type == "multiview":
            p_xz = self.view_xz.make_plot()
            p_xz.xaxis.axis_label = "x"
            p_xz.yaxis.axis_label = "z"

            p_yz = self.view_yz.make_plot()
            p_yz.xaxis.axis_label = "y"
            p_yz.yaxis.axis_label = "z"

            p_xy = self.view_xy.make_plot()
            p_xy.xaxis.axis_label = "x"
            p_xy.yaxis.axis_label = "y"

        elif self.view_control.layout_type != "singleview":
            raise ValueError(f"Invalid layout type: {self.view_control.layout_type}")

        p_projection = self.projection_view.make_plot()
        p_projection.xaxis.axis_label = "b1 (projection)"
        p_projection.yaxis.axis_label = "b2 (projection)"

        if self.view_control.layout_type == "multiview":
            layout = column(
                self.title_div,
                row(p_xy, p_projection),
                row(p_xz, p_yz),
                margin=(0, 20),
            )
        elif self.view_control.layout_type == "singleview":
            layout = column(
                self.title_div,
                p_projection,
                margin=(0, 20),
            )
        else:
            raise ValueError(f"Invalid layout type: {self.view_control.layout_type}")

        if self._layout is None:
            self._layout = layout
        return layout

    def update_layout(self):
        """Update the layout if it has already been created."""

        if self._layout is not None:
            layout = self.make_layout(
                styles=self._styles,
            )
            self._layout.children = layout.children
