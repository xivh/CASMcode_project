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

        self._p_xz = None
        self._p_yz = None
        self._p_xy = None
        self._p_projection = None
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

    def _plots(self):
        plots = []
        if self._p_xz is not None:
            plots.append(self._p_xz)
        if self._p_yz is not None:
            plots.append(self._p_yz)
        if self._p_xy is not None:
            plots.append(self._p_xy)
        if self._p_projection is not None:
            plots.append(self._p_projection)
        return plots

    def set_grid_visibility(self, value: bool):

        for plot in self._plots():
            plot.xgrid.visible = value
            plot.ygrid.visible = value

    def set_transparent(self):

        self.set_grid_visibility(False)

        for plot in self._plots():

            # Make title clear
            plot.title.text_alpha = 0.0

            # Make axes invisible
            plot.xaxis.major_tick_line_alpha = 0.0
            plot.xaxis.minor_tick_line_alpha = 0.0
            plot.xaxis.axis_line_alpha = 0.0
            plot.yaxis.major_tick_line_alpha = 0.0
            plot.yaxis.minor_tick_line_alpha = 0.0
            plot.yaxis.axis_line_alpha = 0.0

            # Make axes labels invisible
            plot.xaxis.major_label_text_alpha = 0.0
            plot.yaxis.major_label_text_alpha = 0.0
            plot.xaxis.axis_label_text_alpha = 0.0
            plot.yaxis.axis_label_text_alpha = 0.0

            # Clear grids
            plot.xgrid.visible = False
            plot.ygrid.visible = False

            # Clear background and borders
            plot.background_fill_alpha = 0.0
            plot.border_fill_alpha = 0.0
            plot.outline_line_alpha = 0.0

    def set_not_transparent(self):
        for plot in self._plots():
            # Make title visible
            plot.title.text_alpha = 1.0

            # Make axes visible
            plot.xaxis.major_tick_line_alpha = 1.0
            plot.xaxis.minor_tick_line_alpha = 1.0
            plot.xaxis.axis_line_alpha = 1.0
            plot.yaxis.major_tick_line_alpha = 1.0
            plot.yaxis.minor_tick_line_alpha = 1.0
            plot.yaxis.axis_line_alpha = 1.0

            # Make axes labels visible
            plot.xaxis.major_label_text_alpha = 1.0
            plot.yaxis.major_label_text_alpha = 1.0
            plot.xaxis.axis_label_text_alpha = 1.0
            plot.yaxis.axis_label_text_alpha = 1.0

            # Restore grids
            plot.xgrid.visible = self.view_control.misc_show_grid_lines
            plot.ygrid.visible = self.view_control.misc_show_grid_lines

            # Restore background and borders
            plot.background_fill_alpha = 1.0
            plot.border_fill_alpha = 1.0
            plot.outline_line_alpha = 1.0

    def set_transparency_mode(self, value: bool):
        if value:
            self.set_transparent()
        else:
            self.set_not_transparent()

    def make_layout(
        self,
        styles: DashboardStyles,
    ):
        self._styles = styles

        if self.view_control.layout_type == "multiview":
            p_xz = self.view_xz.make_plot()
            p_xz.xaxis.axis_label = "x"
            p_xz.yaxis.axis_label = "z"
            self._p_xz = p_xz

            p_yz = self.view_yz.make_plot()
            p_yz.xaxis.axis_label = "y"
            p_yz.yaxis.axis_label = "z"
            self._p_yz = p_yz

            p_xy = self.view_xy.make_plot()
            p_xy.xaxis.axis_label = "x"
            p_xy.yaxis.axis_label = "y"
            self._p_xy = p_xy

        elif self.view_control.layout_type != "singleview":
            raise ValueError(f"Invalid layout type: {self.view_control.layout_type}")

        p_projection = self.projection_view.make_plot()
        self._p_projection = p_projection
        p_projection.xaxis.axis_label = "b1 (projection)"
        p_projection.yaxis.axis_label = "b2 (projection)"

        self.set_grid_visibility(self.view_control.misc_show_grid_lines)
        self.set_transparency_mode(self.view_control.misc_transparency_mode)

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
