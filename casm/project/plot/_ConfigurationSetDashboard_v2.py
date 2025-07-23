import typing

import libcasm.configuration as casmconfig

from ._ProjectionView import ProjectionView
from ._ViewControl import ViewControl


class ConfigurationSetDashboardv2:
    """Dashboard for viewing Configurations from a ConfigurationSet"""

    def __init__(
        self,
        prim: casmconfig.Prim,
        configuration_set: casmconfig.ConfigurationSet,
        component_params: typing.Optional[dict] = None,
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
        """

        self.prim = prim
        """libcasm.configuration.Prim: The primitive cell."""

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

    def make_layout(self):
        # styles = DashboardStyles()

        ### Controls / Widgets / Views construction - begin ###

        # These should be constructed using attributes set in __init__
        # They can be updated by callbacks, but it must be deterministic based on the
        # inputs, no cycles!

        self.projection_view = ProjectionView(view_control=self.view_control)

        ### Controls / Widgets / Views construction - end ###

        ### The trigger_update callback - begin ###

        # Create a trigger_update method as an attribute of the dashboard that
        # updates the projection_view

        def _trigger_update():
            if self.selected_structure is None:
                return

            self.projection_view.set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_structure_name,
            )
            self.projection_view.view_cabinet.plot.title.text = self.selected_name

        self.trigger_update = _trigger_update

        ### The trigger_update callback - end ###

        ### Build and return the layout ###
