import pathlib
import typing

from bokeh.layouts import column, row
from bokeh.models import Spacer

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal

from ._DashboardStyles import DashboardStyles
from ._OpenWithButton import OpenWithButton, vesta_installed
from ._ProjectionView import ProjectionView
from ._ViewControl import ViewControl

# As the simplest dashboard, this can be used a template for more complex dashboards


class StructureDashboard:
    """Bokeh dashboard for viewing a CASM structure."""

    def __init__(
        self,
        structure: xtal.Structure,
        structure_name: str,
        component_params: typing.Optional[dict] = None,
        views_dir: typing.Optional[pathlib.Path] = None,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        structure: libcasm.xtal.Structure
            The :class:`~libcasm.xtal.Structure` to visualize.

        structure_name: str
            The name of the structure to visualize, used as a label in the view.

        component_params: dict[str, dict]
            The bokeh scatter plot parameters used to draw atoms, with
            atom type name as key.

            Must include "color", "radius_pm", and "alpha". Additional bokeh plotting
            parameters like "line_color" and "line_width" may also be included. The
            same attributes must be present for all components.

        views_dir: typing.Optional[pathlib.Path] = None
            The directory to save view files for use saving / loading state. If None,
            views will not be saved.
        """

        self.prim = casmconfig.Prim(
            xtal.Prim.from_atom_coordinates(structure=structure)
        )
        """libcasm.configuration.Prim: The primitive cell, constructed from the 
        structure being visualized."""

        self.views_dir = views_dir
        """pathlib.Path: The directory to save view files for use saving / loading
        state. If None, views will not be saved."""

        self.view_control = ViewControl(
            prim=self.prim,
            component_params=component_params,
        )

        ### Dashboard inputs - begin ###

        self.selected_structure = structure
        """libcasm.xtal.Structure: The structure to view in projection_view."""

        self.selected_structure_name = structure_name
        """str: The name of the selected structure, used as a label in 
        projection_view."""

        ### Dashboard inputs - end ###

        self.open_with_vesta_button = OpenWithButton(
            parent=self,
        )

    def make_layout(self):
        styles = DashboardStyles()

        ### Controls / Widgets / Views construction - begin ###

        # These should be constructed using attributes set in __init__
        # They can be updated by callbacks, but it must be deterministic based on the
        # inputs, no cycles!

        self.projection_view = ProjectionView(view_control=self.view_control)

        if self.selected_structure is not None:
            self.projection_view.set_structure(
                structure=self.view_control.make_superstructure(
                    init_structure=self.selected_structure,
                ),
                name=self.selected_structure_name,
            )

        ### Controls / Widgets / Views construction - end ###

        ### The trigger_update callback - begin ###

        # Create a trigger_update method as an attribute of the dashboard that
        # updates the projection_view

        def _trigger_update():

            if self.selected_structure is None:
                return

            self.projection_view.set_structure(
                structure=self.view_control.make_superstructure(
                    init_structure=self.selected_structure,
                ),
                name=self.selected_structure_name,
            )

        self.trigger_update = _trigger_update

        ### The trigger_update callback - end ###

        ### Build and return the layout ###

        control_layout, settings_switch = self.view_control.make_controls_tabs_layout(
            select_control_layout=None,
            styles=styles,
            parent=self,
            views_dir=self.views_dir,
        )

        # Figures grid
        projection_view_layout = self.projection_view.make_layout(
            styles=styles,
        )

        # Top row:
        row_elements = []
        if vesta_installed():
            open_with_vesta_button_layout = self.open_with_vesta_button.make_layout(
                styles=styles
            )
            row_elements += [
                Spacer(width=20, sizing_mode="stretch_width"),
                open_with_vesta_button_layout,
            ]
        row_elements += [
            column(
                settings_switch,
                margin=(20, 20),
            )
        ]
        select_layout = row(
            *row_elements,
            sizing_mode="stretch_width",
        )

        # Overall layout
        layout = column(
            select_layout,
            control_layout,
            projection_view_layout,
        )

        return layout
