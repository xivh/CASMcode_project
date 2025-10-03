import pathlib
import typing

from bokeh.layouts import column, row
from bokeh.models import Spacer

import libcasm.configuration as casmconfig

from ._ConfigurationSetSelect import ConfigurationSetSelect
from ._DashboardStyles import DashboardStyles
from ._OpenWithButton import OpenWithButton, vesta_installed
from ._ProjectionView import ProjectionView
from ._ViewControl import ViewControl


class ConfigurationSetDashboardv2:
    """Dashboard for viewing Configurations from a ConfigurationSet"""

    def __init__(
        self,
        prim: casmconfig.Prim,
        configuration_set: casmconfig.ConfigurationSet,
        component_params: typing.Optional[dict] = None,
        views_dir: typing.Optional[pathlib.Path] = None,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        prim: libcasm.configuration.Prim
            The primitive cell.

        configuration_set: libcasm.configuration.ConfigurationSet
            The :class:`~libcasm.configuration.ConfigurationSet` to visualize.

        component_params: dict[str, dict]
            The bokeh scatter plot parameters used to draw atoms, with
            atom type name as key.

            Must include "color", "size", and "alpha". Additional bokeh plotting
            parameters like "line_color" and "line_width" may also be included. The
            same attributes must be present for all components.

        views_dir: typing.Optional[pathlib.Path] = None
            The directory to save view files for use saving / loading state. If None,
            views will not be saved.
        """

        self.prim = prim
        """libcasm.configuration.Prim: The primitive cell."""

        self.views_dir = views_dir
        """pathlib.Path: The directory to save view files for use saving / loading
        state. If None, views will not be saved."""

        self.view_control = ViewControl(
            prim=self.prim,
            component_params=component_params,
        )

        ### Dashboard inputs - begin ###

        self.configuration_set = configuration_set
        """libcasm.configuration.ConfigurationSet: The ConfigurationSet to visualize."""

        self.selected_structure = None
        """libcasm.xtal.Structure: The structure to view in projection_view."""

        self.selected_structure_name = None
        """str: The name of the selected structure, used as a label in 
        projection_view."""

        ### Dashboard inputs - end ###

        self.configuration_set_select = ConfigurationSetSelect(
            configuration_set=self.configuration_set,
            parent=self,
        )

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

        select_layout = self.configuration_set_select.make_layout(styles=styles)

        control_layout = self.view_control.make_controls_tabs_layout(
            select_control_layout=None,
            styles=styles,
            parent=self,
            views_dir=self.views_dir,
        )

        # Figures grid
        projection_view_layout = self.projection_view.make_layout(
            styles=styles,
        )

        if vesta_installed():
            open_with_vesta_button_layout = self.open_with_vesta_button.make_layout(
                styles=styles
            )
            select_layout = row(
                select_layout,
                Spacer(width=20, sizing_mode="stretch_width"),
                open_with_vesta_button_layout,
                sizing_mode="stretch_width",
            )

        # Overall layout
        layout = column(
            select_layout,
            control_layout,
            projection_view_layout,
            margin=(20, 0),
        )

        return layout
