import copy
import json
import math
import pathlib
import typing

import bokeh.models
import numpy as np
import scipy.spatial.transform
from bokeh.layouts import column, row

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal

from ._DashboardStyles import DashboardStyles
from ._misc import (
    from_miller_bravais_direction,
    scale_to_int_if_possible,
    to_miller_bravais_direction,
)
from ._view import (
    CabinetProjection,
    IsometricProjection,
    SinglePointProjection,
    make_projection_from_dict,
)
from ._ViewAtomicStructure import (
    adjust_color,
    make_highlight_params,
    make_prim_component_params,
)


class ProjectionAxesInput:
    def __init__(
        self,
        view_control,
        styles: DashboardStyles = None,
        parent: typing.Any = None,
    ):
        """

        Parameters
        ----------
        view_control : ViewControl
            The view control object that manages the view parameters.
        styles : DashboardStyles
            Used to style the Bokeh widgets.
        parent: typing.Any
            A Dashboard object, used to call ``parent.trigger_update()``.

        """
        self.view_control = view_control
        self.styles = styles
        self.parent = parent
        # self.projection_view = projection_view

        # -- Make widgets ---

        # -- Output current view axes --
        self.view_basis_cart = None
        self.view_basis_frac = None
        self.view_basis_mb = None
        self.projection_rotation_angle_row = None

        self._update_view_basis()

        # Axes priority/order
        # self.projaxes_input_order_div = bokeh.models.Div(
        #     text="""<b>Axes to set</b>""", width=200
        # )
        self.projaxes_input_order_select = bokeh.models.Select(
            options=[key for key in self.view_control.projaxes_input_order_options],
            value=self.view_control.projaxes_input_order,
            stylesheets=[self.styles.dark_bk_input_style],
            title="Axes to set",
            description="Set the horizontal axis (b1), "
            "the vertical axis (b2), and the out-of-plane axis (b3) "
            "in the order specified. The first axis is set exactly, "
            "the second made orthogonal to the first, "
            "and the third set orthogonal to those.",
            align="end",
        )

        # Input mode
        # self.projaxes_input_mode_div = bokeh.models.Div(
        #     text="""<b>Input mode</b>""", width=200
        # )
        options = [
            ("frac", "Fractional"),
            ("cart", "Cartesian"),
            ("miller_bravais", "Miller-Bravais"),
        ]
        self.projaxes_input_mode_select = bokeh.models.Select(
            title="Mode",
            options=options,
            value=self.view_control.projaxes_input_mode,
            stylesheets=[self.styles.dark_bk_input_style],
        )

        # Update view button:
        self.update_button = bokeh.models.Button(
            label="Update view",
            button_type="success",
            align="end",
        )

        # -- Spinners --

        self.spinner = dict()

        # -- Cart spinnners --
        cart_spinner = [[], [], []]
        for b in range(3):
            for i in range(3):
                cart_spinner[b].append(
                    bokeh.models.Spinner(
                        title=f"b{b+1}{i + 1}",
                        value=0,
                        stylesheets=[self.styles.dark_bk_input_style],
                        format="0.0",
                        **dict(width=80, low=None, high=None, step=0.1),
                    )
                )
        self.spinner["cart"] = cart_spinner

        # -- Frac spinners --
        frac_spinner = [[], [], []]
        for b in range(3):
            for i in range(3):
                frac_spinner[b].append(
                    bokeh.models.Spinner(
                        title=f"b{b+1}{i + 1}",
                        value=0,
                        stylesheets=[self.styles.dark_bk_input_style],
                        **dict(width=80, low=None, high=None, step=1),
                    )
                )
        self.spinner["frac"] = frac_spinner

        # -- Miller-Bravais spinners --
        miller_bravais_spinner = [[], [], []]
        for b in range(3):
            for i in range(4):
                miller_bravais_spinner[b].append(
                    bokeh.models.Spinner(
                        title=f"b{b+1}{i + 1}",
                        value=0,
                        stylesheets=[self.styles.dark_bk_input_style],
                        **dict(width=80, low=None, high=None, step=1),
                    )
                )
        self.spinner["miller_bravais"] = miller_bravais_spinner

        # -- Callbacks --

        def update_projaxes_input_mode(attr, old, new):
            self.update_layout()

        self.projaxes_input_mode_select.on_change("value", update_projaxes_input_mode)

        def update_projaxes_input_order(attr, old, new):
            self.update_layout()

        self.projaxes_input_order_select.on_change("value", update_projaxes_input_order)

        def update_view_action(attr):
            self.update_view()
            self.update_layout()

        self.update_button.on_click(update_view_action)

        # -- Layout --
        self.make_layout()

    @property
    def projection_view(self):
        return self.parent.projection_view.projection_view

    def _make_view_basis_div(self, B):

        B1 = scale_to_int_if_possible(B[0], cutoff=10)
        B2 = scale_to_int_if_possible(B[1], cutoff=10)
        B3 = scale_to_int_if_possible(B[2], cutoff=10)

        return column(
            row(
                bokeh.models.Div(text="""<b>b1:""", width=40),
                *[
                    bokeh.models.Div(text=f"""<b>{B1[i]:.3f}""", width=80)
                    for i in range(len(B1))
                ],
            ),
            row(
                bokeh.models.Div(text="""<b>b2:""", width=40),
                *[
                    bokeh.models.Div(text=f"""<b>{B2[i]:.3f}""", width=80)
                    for i in range(len(B2))
                ],
            ),
            row(
                bokeh.models.Div(text="""<b>b3:""", width=40),
                *[
                    bokeh.models.Div(text=f"""<b>{B3[i]:.3f}""", width=80)
                    for i in range(len(B3))
                ],
            ),
        )

    def _update_view_basis(self):
        view_basis = self.projection_view.view_basis

        # Cart vectors
        B = [
            view_basis[:, 0],
            view_basis[:, 1],
            view_basis[:, 2],
        ]
        col = self._make_view_basis_div(B)
        if self.view_basis_cart is None:
            self.view_basis_cart = col
        else:
            self.view_basis_cart.children = col.children

        # Frac vectors
        L = self.view_control.prim.xtal_prim.lattice().column_vector_matrix()
        L_inv = np.linalg.inv(L)
        B = [
            L_inv @ view_basis[:, 0],
            L_inv @ view_basis[:, 1],
            L_inv @ view_basis[:, 2],
        ]
        col = self._make_view_basis_div(B)
        if self.view_basis_frac is None:
            self.view_basis_frac = col
        else:
            self.view_basis_frac.children = col.children

        # Miller-Bravais vectors
        B = [
            to_miller_bravais_direction(L_inv @ view_basis[:, 0]),
            to_miller_bravais_direction(L_inv @ view_basis[:, 1]),
            to_miller_bravais_direction(L_inv @ view_basis[:, 2]),
        ]
        col = self._make_view_basis_div(B)
        if self.view_basis_mb is None:
            self.view_basis_mb = col
        else:
            self.view_basis_mb.children = col.children

        # # Cabinet scale display
        # r = row(
        #     bokeh.models.Div(text="""<b>Cabinet scale: </b>""", width=140),
        #     bokeh.models.Div(
        #         text=f"""<b>{self.view_control.cabinet_scale:.3f}</b>""",
        #         width=80,
        #     ),
        # )
        # if self.cabinet_scale_row is None:
        #     self.cabinet_scale_row = r
        # else:
        #     self.cabinet_scale_row.children = r.children
        #
        # # Cabinet angle display
        # angle = self.view_control.cabinet_angle * 180 / math.pi
        # r = row(
        #     bokeh.models.Div(text="""<b>Cabinet angle: </b>""", width=140),
        #     bokeh.models.Div(
        #         text=f"""<b>{(angle):.3f}</b>""",
        #         width=80,
        #     ),
        # )
        # if self.cabinet_angle_row is None:
        #     self.cabinet_angle_row = r
        # else:
        #     self.cabinet_angle_row.children = r.children

        # Cabinet rotation angle display
        r = row(
            bokeh.models.Div(text="""<b>Rotation angle: </b>""", width=140),
            bokeh.models.Div(
                text=f"""<b>{self.view_control.projection_rotation_angle:.3f}</b>""",
                width=80,
            ),
        )
        if self.projection_rotation_angle_row is None:
            self.projection_rotation_angle_row = r
        else:
            self.projection_rotation_angle_row.children = r.children

    def make_layout(self):
        mode = self.projaxes_input_mode_select.value
        order = self.projaxes_input_order_select.value
        order_options = self.view_control.projaxes_input_order_options
        priority = order_options[order]

        mode_frac = "frac"
        mode_cart = "cart"
        mode_mb = "miller_bravais"

        # Display of current projection view basis
        self.view_basis_cart.visible = mode == mode_cart
        self.view_basis_frac.visible = mode == mode_frac
        self.view_basis_mb.visible = mode == mode_mb

        # Input of new projection view basis
        self.spinner_frac_input = column(
            row(*[x for x in self.spinner[mode_frac][priority[0] - 1]]),
            row(*[x for x in self.spinner[mode_frac][priority[1] - 1]]),
        )
        self.spinner_frac_input.visible = mode == mode_frac
        self.spinner_cart_input = column(
            row(*[x for x in self.spinner[mode_cart][priority[0] - 1]]),
            row(*[x for x in self.spinner[mode_cart][priority[1] - 1]]),
        )
        self.spinner_cart_input.visible = mode == mode_cart
        self.spinner_mb_input = column(
            row(*[x for x in self.spinner[mode_mb][priority[0] - 1]]),
            row(*[x for x in self.spinner[mode_mb][priority[1] - 1]]),
        )
        self.spinner_mb_input.visible = mode == mode_mb

        self.layout = row(
            column(
                self.projaxes_input_mode_select,
                bokeh.models.Div(text="""<b>Current axes: </b>""", width=200),
                self.view_basis_frac,
                self.view_basis_cart,
                self.view_basis_mb,
                # self.cabinet_scale_row,
                # self.cabinet_angle_row,
                self.projection_rotation_angle_row,
                height=250,
                width=400,
            ),
            column(
                row(
                    self.projaxes_input_order_select,
                    self.update_button,
                ),
                bokeh.models.Div(text="""<b>New axes: </b>""", width=200),
                self.spinner_frac_input,
                self.spinner_cart_input,
                self.spinner_mb_input,
                height=250,
                width=400,
                margin=(0, 10),
            ),
        )

    def update_layout(self):
        mode = self.projaxes_input_mode_select.value
        # order = self.projaxes_input_order_select.value
        # order_options = self.view_control.projaxes_input_order_options
        # priority = order_options[order]
        # self.layout.children = [
        #     self.projaxes_input_mode_select,
        #     self.projaxes_input_order_select,
        #     self.update_button,
        #     row(*[x for x in self.spinner[mode][priority[0] - 1]]),
        #     row(*[x for x in self.spinner[mode][priority[1] - 1]]),
        # ]

        self._update_view_basis()

        # First hide currently visible spinner
        if self.spinner_frac_input.visible and mode != "frac":
            self.view_basis_frac.visible = False
            self.spinner_frac_input.visible = False
        if self.spinner_cart_input.visible and mode != "cart":
            self.view_basis_cart.visible = False
            self.spinner_cart_input.visible = False
        if self.spinner_mb_input.visible and mode != "miller_bravais":
            self.view_basis_mb.visible = False
            self.spinner_mb_input.visible = False

        if mode == "frac":
            self.view_basis_frac.visible = True
            self.spinner_frac_input.visible = True
        if mode == "cart":
            self.view_basis_cart.visible = True
            self.spinner_cart_input.visible = True
        if mode == "miller_bravais":
            self.view_basis_mb.visible = True
            self.spinner_mb_input.visible = True

    def update_view(self):
        # -- Get the view input --

        # - Input mode -
        mode = self.projaxes_input_mode_select.value
        self.view_control.projaxes_input_mode = mode

        order = self.projaxes_input_order_select.value
        self.view_control.projaxes_input_order = order

        order_options = self.view_control.projaxes_input_order_options
        priority = order_options[order]

        # Highest priority input (match this direction exactly)
        x = [s.value for s in self.spinner[mode][priority[0] - 1]]
        self.view_control.projection_first_input = np.array(x)

        # Second highest priority input (make orthogonal to the first)
        x = [s.value for s in self.spinner[mode][priority[1] - 1]]
        self.view_control.projection_second_input = np.array(x)

        # -- Update the projection view axes --
        self.view_control.set_projection_view_axes()

        # -- Trigger view update --
        self.parent.trigger_update()


class ViewControl:
    def __init__(
        self,
        prim: casmconfig.Prim,
        component_params: typing.Optional[dict] = None,
        projection: typing.Any = None,
    ):
        self.prim = prim

        self.component_params = copy.deepcopy(component_params)
        if self.component_params is None:
            self.component_params = make_highlight_params(
                component_params=make_prim_component_params(prim=self.prim),
            )

        self.selected_color_factor = -0.3

        if projection is None:
            projection = SinglePointProjection()

        self._initial_projection = projection
        self.projection = projection
        self.parent = None

        ### Widgets: ###
        self._widgets = dict()
        self._projaxes_input = None

        ### Reset: ###

        self.reset()

    def reset_images(self):
        self.images_a_range = 1
        """int: The number of periodic images to show along the a-axis"""

        self.images_b_range = 1
        """int: The number of periodic images to show along the a-axis"""

        self.images_c_range = 1
        """int: The number of periodic images to show along the a-axis"""

        self.images_m_range = 1
        """int: The number of periodic images to show along the a-, b-, and c-axis"""

    def reset_markers(self):
        self.marker_size_scale = 1.0
        """float: The scale factor for the marker size"""

        self.marker_alpha_scale = 1.0
        """float: The alpha value for the marker alpha"""

        # component_params = copy.deepcopy(self._input_component_params)
        # if component_params is None:
        #     component_params = make_prim_component_params(prim=self.prim)
        # self.component_params = component_params
        # """dict[str, dict]: The bokeh scatter plot parameters used to draw atoms, with
        # atom type name as key.
        #
        # Must include "color", "radius_pm", and "alpha". Additional bokeh plotting
        # parameters like "line_color" and "line_width" may also be included. The
        # same attributes must be present for all components.
        # """

    def reset_component_params(
        self,
        component_params: typing.Optional[dict] = None,
    ):
        # self._input_component_params = copy.deepcopy(component_params)
        # component_params = copy.deepcopy(self._input_component_params)
        if component_params is None:
            component_params = make_prim_component_params(prim=self.prim)
        self.component_params = component_params
        """dict[str, dict]: The bokeh scatter plot parameters used to draw atoms, with
        atom type name as key.

        Must include "color", "radius_pm", and "alpha". Additional bokeh plotting
        parameters like "line_color" and "line_width" may also be included. The
        same attributes must be present for all components.
        """

    def reset_layout_type(
        self,
    ):
        self.layout_type = "singleview"
        """str: The layout of the views; one of "multiview" or "singleview"."""

        self.multiview_figure_params = {
            "width": 600,
            "height": 400,
            "match_aspect": True,
        }

        self.singleview_figure_params = {
            "width": 1200,
            "height": 800,
            "match_aspect": True,
        }
        """dict: The parameters passed to bokeh.figure() when making the plots."""

        self.title_params = {
            "width": 1200,
            "height": 50,  # Sufficient height for the text
            "styles": {
                "display": "flex",  # Make the Div a flex container
                # "justify-content": "center",  # Center content horizontally
                "align-items": "center",  # Center content vertically
                "font-size": "32px",  # Adjust font size
                "padding-bottom": "10px",  # Add some space below
                # 'border': '1px solid red' # Uncomment for debugging to see bounds
            },
        }

    def reset_projection_view(self):
        # self.cabinet_scale = 0.2
        # """float: The scale factor for the projection view"""
        #
        # self.cabinet_angle = math.pi / 6.0
        # """float: The angle for the projection view"""
        # self.projection = self._initial_projection

        self.projection_rotation_angle = 10.0
        """float: The angle to rotate, in degrees"""

        self.projection_v1 = np.array([1.0, 0.0, 0.0])
        """np.array[float]: The Cartesian vector for the horizontal axis of the 
        projection view."""

        self.projection_v2 = np.array([0.0, 0.0, 1.0])
        """np.array[float]: The Cartesian vector for the vertical axis of the 
        projection view."""

        self.projection_first_input = np.array([1.0, 0.0, 0.0])
        """np.array[float]: The Cartesian vector for the horizontal axis of the
        projection view."""

        self.projection_second_input = np.array([0.0, 0.0, 1.0])
        """np.array[float]: The Cartesian vector for the vertical axis of the
        projection view."""

        self.projaxes_input_mode = "cart"
        """str: projection view axes input mode; one of "frac", "cart", or 
        "miller_bravais"."""

        self.projaxes_input_order_options = {
            "b1, b2": [1, 2, 3],
            "b1, b3": [1, 3, 2],
            "b3, b1": [3, 1, 2],
            "b3, b2": [3, 2, 1],
            "b2, b1": [2, 1, 3],
            "b2, b3": [2, 3, 1],
        }
        """dict: Options for the projection view axes input order."""

        self.projaxes_input_order = "b1, b2"
        """str: The current input order, as a key into 
        `projaxes_input_order_options`."""

    def reset(self):
        self.reset_images()
        self.reset_markers()
        self.reset_projection_view()
        self.reset_layout_type()
        self.projection = self._initial_projection

        # Misc.
        self.misc_show_grid_lines = True
        self.misc_transparency_mode = False

        self._update_disabled = False
        """bool: Flag used internally to prevent triggering updates in some callbacks"""

    def _vector_to_cart(self, v):
        if v is None:
            return np.zeros((3,))
        L = self.prim.xtal_prim.lattice().column_vector_matrix()
        if self.projaxes_input_mode == "cart":
            return v
        elif self.projaxes_input_mode == "frac":
            return L @ v
        elif self.projaxes_input_mode == "miller_bravais":
            return L @ from_miller_bravais_direction(v)
        else:
            raise Exception("projection view input mode error")

    def _vector_from_cart(self, v):
        size = 3
        if self.projaxes_input_mode == "miller_bravais":
            size = 4
        if v is None:
            return np.zeros((size,))
        if self.projaxes_input_mode == "cart":
            return v
        elif self.projaxes_input_mode == "frac":
            L = self.prim.xtal_prim.lattice().column_vector_matrix()
            return np.linalg.pinv(L) @ v
        elif self.projaxes_input_mode == "miller_bravais":
            L = self.prim.xtal_prim.lattice().column_vector_matrix()
            v_frac = np.linalg.pinv(L) @ v
            return to_miller_bravais_direction(v_frac)
        else:
            raise Exception("projection view input mode error")

    def set_projection_view_axes(
        self,
    ):
        """Set the projection view axes"""

        priority = self.projaxes_input_order_options[self.projaxes_input_order]
        if len(priority) != 3 or list(set(priority)) != [1, 2, 3]:
            raise Exception(
                "projection view priority must be a permutation of [1, 2, 3]"
            )

        input_axes = np.zeros((3, 3))
        input_axes[:, priority[0] - 1] = self._vector_to_cart(
            self.projection_first_input
        )
        input_axes[:, priority[1] - 1] = self._vector_to_cart(
            self.projection_second_input
        )
        input_axes[:, priority[2] - 1] = self._vector_to_cart(None)

        # Build the new axes
        new_axes = np.zeros((3, 3))
        first = None
        second = None
        third = None
        # [1, 2, 3] -> b3 = np.cross(b1, b2)
        # [1, 3, 2] -> b2 = -np.cross(b1, b3)
        for i_order, i_axis in enumerate(priority):
            if i_order == 0:
                x = input_axes[:, i_axis - 1]
                norm = np.linalg.norm(x)
                if np.isclose(norm, 0):
                    raise Exception(
                        "Highest priority projection view axis cannot be length zero"
                    )
                first = x / norm
                new_axes[:, i_axis - 1] = first
            elif i_order == 1:
                x = input_axes[:, i_axis - 1]
                second = x - (x @ first) * first
                norm = np.linalg.norm(second)
                if np.isclose(norm, 0):
                    raise Exception(
                        "Second highest priority projection view axis cannot be "
                        "parallel to the highest priority view axis"
                    )
                second = second / np.linalg.norm(second)
                new_axes[:, i_axis - 1] = second
            elif i_order == 2:
                if priority == [1, 2, 3]:
                    third = np.cross(first, second)
                elif priority == [1, 3, 2]:
                    third = -np.cross(first, second)
                elif priority == [3, 1, 2]:
                    third = np.cross(first, second)
                elif priority == [3, 2, 1]:
                    third = -np.cross(first, second)
                elif priority == [2, 1, 3]:
                    third = -np.cross(first, second)
                elif priority == [2, 3, 1]:
                    third = np.cross(first, second)
                else:
                    raise Exception("projection view basis construction priority error")
                new_axes[:, i_axis - 1] = third
            else:
                raise Exception("projection view basis construction error")

        self.projection_v1 = new_axes[:, 0]
        self.projection_v2 = new_axes[:, 1]

        self.projection_first_input = self._vector_from_cart(
            new_axes[:, priority[0] - 1]
        )
        self.projection_second_input = self._vector_from_cart(
            new_axes[:, priority[1] - 1]
        )

    def rotate_projection_view_basis(
        self,
        v_axis: np.ndarray,
        view_basis: np.ndarray,
        angle: float,
    ):
        """Rotate the view basis vectors by an angle about an axis.

        Parameters
        ----------
        v_axis: np.ndarray
            The axis to rotate about. Will be normalized.
        view_basis: np.ndarray
            The current view basis vectors, as columns of a 3x3 matrix.
        angle: float
            The angle to rotate by in degrees.

        """
        v_axis = np.array(v_axis)
        v_axis_normalized = v_axis / np.linalg.norm(v_axis)

        # Convert angle from degrees to radians
        angle_rad = np.deg2rad(angle)

        # Get the rotation matrix
        rotation = scipy.spatial.transform.Rotation.from_rotvec(
            v_axis_normalized * angle_rad
        )
        rotation_matrix = rotation.as_matrix()

        # Rotate the view basis
        new_view_basis = view_basis @ rotation_matrix

        # Set the new projection_v1 and projection_v2
        self.projection_v1 = new_view_basis[:, 0]
        self.projection_v2 = new_view_basis[:, 1]

    def get_state(self):
        return {
            #
            # Images parameters
            "a_range": self.images_a_range,
            "b_range": self.images_b_range,
            "c_range": self.images_c_range,
            "m_range": self.images_m_range,
            #
            # Markers parameters
            "marker_size_scale": self.marker_size_scale,
            "marker_alpha_scale": self.marker_alpha_scale,
            #
            # Colors parameters
            "selected_color_factor": self.selected_color_factor,
            "component_params": self.component_params,
            #
            # Projection parameters
            "initial_projection": self._initial_projection.to_dict(),
            "projection": self.projection.to_dict(),
            "projection_v1": self.projection_v1.tolist(),
            "projection_v2": self.projection_v2.tolist(),
            "projection_rotation_angle": self.projection_rotation_angle,
            "projaxes_input_order": self.projaxes_input_order,
            "projaxes_input_mode": self.projaxes_input_mode,
            #
            # Layout parameters
            "layout_type": self.layout_type,
            "multiview_figure_params": self.multiview_figure_params,
            "singleview_figure_params": self.singleview_figure_params,
            #
            # Misc parameters
            "misc_show_grid_lines": self.misc_show_grid_lines,
            "misc_transparency_mode": self.misc_transparency_mode,
        }

    def set_state(
        self,
        state: dict,
    ):

        # Image parameters
        self.images_a_range = state.get("a_range", 1)
        self.images_b_range = state.get("b_range", 1)
        self.images_c_range = state.get("c_range", 1)
        self.images_m_range = state.get("m_range", 1)

        # Marker parameters
        self.marker_size_scale = state.get("marker_size_scale", 1.0)
        self.marker_alpha_scale = state.get("marker_alpha_scale", 1.0)

        # Colors parameters
        self.selected_color_factor = state.get("selected_color_factor", -0.3)
        self.component_params = state.get("component_params", {})

        # Projection parameters
        self._initial_projection = make_projection_from_dict(
            state.get(
                "initial_projection",
                SinglePointProjection().to_dict(),
            )
        )
        self.projection = make_projection_from_dict(
            state.get(
                "projection",
                SinglePointProjection().to_dict(),
            )
        )
        self.projection_v1 = np.array(state.get("projection_v1", [1.0, 0.0, 0.0]))
        self.projection_v2 = np.array(state.get("projection_v2", [0.0, 0.0, 1.0]))
        self.projection_rotation_angle = state.get("projection_rotation_angle", 10.0)
        self.projaxes_input_order = state.get("projaxes_input_order", "b1, b2")
        self.projaxes_input_mode = state.get("projaxes_input_mode", "cart")

        # Layout parameters
        self.layout_type = state.get("layout_type", "singleview")
        self.multiview_figure_params = state.get(
            "multiview_figure_params",
            {
                "width": 600,
                "height": 400,
                "match_aspect": True,
            },
        )
        self.singleview_figure_params = state.get(
            "singleview_figure_params",
            {
                "width": 1200,
                "height": 800,
                "match_aspect": True,
            },
        )

        # Misc parameters
        self.misc_show_grid_lines = state.get("misc_show_grid_lines", True)
        self.misc_transparency_mode = state.get("misc_transparency_mode", False)

        # Update widgets if they exist:
        if "images" in self._widgets:
            self._update_disabled = True
            self._widgets["images"]["images_a_range"].value = self.images_a_range
            self._widgets["images"]["images_b_range"].value = self.images_b_range
            self._widgets["images"]["images_c_range"].value = self.images_c_range
            self._widgets["images"]["images_m_range"].value = self.images_m_range
            self._update_disabled = False

        if "styles" in self._widgets:
            self._update_disabled = True

            self._widgets["styles"][
                "selected_color_factor_spinner"
            ].value = self.selected_color_factor

            if "radius_spinners_by_name" in self._widgets["styles"]:
                for name, spinner in self._widgets["styles"][
                    "radius_spinners_by_name"
                ].items():
                    if name in self.component_params:
                        spinner.value = self.component_params[name].get(
                            "radius_pm", 100.0
                        )

            if "pickers_by_name" in self._widgets["styles"]:
                for name, picker in self._widgets["styles"]["pickers_by_name"].items():
                    if name in self.component_params:
                        picker.color = self.component_params[name].get(
                            "color", "#000000"
                        )

            # Update line style widgets
            if "line_dash_selects_by_name" in self._widgets["styles"]:
                for name, select in self._widgets["styles"][
                    "line_dash_selects_by_name"
                ].items():
                    if name in self.component_params:
                        select.value = self.component_params[name].get(
                            "line_dash", "solid"
                        )

            if "line_color_pickers_by_name" in self._widgets["styles"]:
                for name, picker in self._widgets["styles"][
                    "line_color_pickers_by_name"
                ].items():
                    if name in self.component_params:
                        picker.color = self.component_params[name].get(
                            "line_color", "#000000"
                        )

            if "line_width_spinners_by_name" in self._widgets["styles"]:
                for name, spinner in self._widgets["styles"][
                    "line_width_spinners_by_name"
                ].items():
                    if name in self.component_params:
                        spinner.value = self.component_params[name].get(
                            "line_width", 1.0
                        )

            self._update_disabled = False

        if "layout" in self._widgets:
            self._update_disabled = True
            self._widgets["layout"]["layout_type_select"].value = self.layout_type
            self._widgets["layout"]["singleview_width_spinner"].value = (
                self.singleview_figure_params.get("width", 1200)
            )
            self._widgets["layout"]["singleview_height_spinner"].value = (
                self.singleview_figure_params.get("height", 800)
            )
            self._widgets["layout"]["multiview_width_spinner"].value = (
                self.multiview_figure_params.get("width", 600)
            )
            self._widgets["layout"]["multiview_height_spinner"].value = (
                self.multiview_figure_params.get("height", 400)
            )
            self._update_disabled = False

        if "misc" in self._widgets:
            self._update_disabled = True
            widgets = self._widgets["misc"]
            widgets["grid_lines_switch"].active = self.misc_show_grid_lines
            widgets["transparency_mode_switch"].active = self.misc_transparency_mode
            self._update_disabled = False

        if self._projaxes_input is not None:
            self.parent.projection_view.update_layout_type()
            self.parent.trigger_update()
            self.parent.projection_view.update_layout()
            self._projaxes_input.update_layout()

    def make_superstructure(
        self,
        init_structure: xtal.Structure,
    ):
        """Make a superstructure from the given structure, based on the current
        parameters.


        Parameters
        ----------
        init_structure: libcasm.xtal.Structure
            The initial structure being viewed.

        Returns
        -------
        superstructure: libcasm.xtal.Structure
            The superstructure view, based on a, b, c, and m.

        """

        a = self.images_a_range
        b = self.images_b_range
        c = self.images_c_range
        m = self.images_m_range
        T = np.diag([a, b, c]) * m
        structure = xtal.make_structure_within(init_structure=init_structure)
        return xtal.make_superstructure(
            transformation_matrix_to_super=T,
            structure=structure,
        )

    def update_highlight_style(
        self,
        highlight_color: str,
        highlight_width: float = 2.0,
    ):
        """Update the highlight (selected component) line color and width in both
        component_params and the corresponding widgets.

        This method updates all selected component parameters and their associated
        widgets to use the specified highlight color and width.

        Parameters
        ----------
        highlight_color : str
            The color to use for highlighted/selected components (e.g., "#FF0000")
        highlight_width : float, optional
            The line width to use for highlighted/selected components (default: 2.0)
        """
        if "styles" not in self._widgets:
            return

        self._update_disabled = True

        # Update component_params for all selected components
        for name, params in self.component_params.items():
            if name.endswith("_sel"):
                params["line_color"] = highlight_color
                params["line_width"] = highlight_width
                params["line_alpha"] = 1.0

        # Update widgets if they exist
        line_color_pickers = self._widgets["styles"].get(
            "line_color_pickers_by_name", {}
        )
        line_width_spinners = self._widgets["styles"].get(
            "line_width_spinners_by_name", {}
        )

        for name in self.component_params.keys():
            if name.endswith("_sel"):
                if name in line_color_pickers:
                    line_color_pickers[name].color = highlight_color
                if name in line_width_spinners:
                    line_width_spinners[name].value = highlight_width

        self._update_disabled = False

    # trigger:
    # self.set_image_index(self.selected_image_index)
    # set_structure(
    #     structure=self.selected_structure.copy(),
    #     name=self.selected_name,
    # )

    def make_images_control_layout(
        self,
        styles=None,
        parent=None,
    ):
        # Periodic range controls
        images_div = bokeh.models.Div(text="""<b># Periodic Images</b>""", width=200)
        params = dict(width=80, low=1, high=None, step=1)
        images_a_range = bokeh.models.Spinner(
            title="Along `a`",
            value=self.images_a_range,
            stylesheets=[styles.dark_bk_input_style],
            **params,
        )
        images_b_range = bokeh.models.Spinner(
            title="Along `b`",
            value=self.images_b_range,
            stylesheets=[styles.dark_bk_input_style],
            **params,
        )
        images_c_range = bokeh.models.Spinner(
            title="Along `c`",
            value=self.images_c_range,
            stylesheets=[styles.dark_bk_input_style],
            **params,
        )
        images_m_range = bokeh.models.Spinner(
            title="Mult.",
            value=self.images_c_range,
            low=1,
            high=None,
            step=1,
            stylesheets=[styles.dark_bk_input_style],
        )

        # Reset button:
        reset_button = bokeh.models.Button(label="Reset", button_type="success")

        def reset_button_action(attr):
            self.reset_images()

            # --- Update the widgets without triggers ---
            self._update_disabled = True
            images_a_range.value = self.images_a_range
            images_b_range.value = self.images_b_range
            images_c_range.value = self.images_c_range
            images_m_range.value = self.images_m_range
            self._update_disabled = False
            # --------------------------------------------

            parent.trigger_update()

        reset_button.on_click(reset_button_action)

        # Periodic range - callbacks
        def update_a_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_a_range = new
            parent.trigger_update()

        def update_b_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_b_range = new
            parent.trigger_update()

        def update_c_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_c_range = new
            parent.trigger_update()

        def update_m_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_m_range = new
            parent.trigger_update()

        images_a_range.on_change("value", update_a_range)
        images_b_range.on_change("value", update_b_range)
        images_c_range.on_change("value", update_c_range)
        images_m_range.on_change("value", update_m_range)

        c1 = column(
            images_div,
            row(images_a_range, images_b_range, images_c_range),
            images_m_range,
            width=300,
            margin=(0, 10),
        )
        c2 = column(
            reset_button,
            width=200,
            margin=(0, 10),
        )

        # Save images widgets:
        self._widgets["images"] = dict()
        self._widgets["images"]["images_a_range"] = images_a_range
        self._widgets["images"]["images_b_range"] = images_b_range
        self._widgets["images"]["images_c_range"] = images_c_range
        self._widgets["images"]["images_m_range"] = images_m_range

        return row(
            c1,
            c2,
            stylesheets=[
                styles.darkstyle,
                styles.typekit_stylesheet,
            ],
        )

    def make_markers_control_layout(
        self,
        styles=None,
        parent=None,
    ):
        # Marker scale controls
        marker_size_scale_div = bokeh.models.Div(
            text="""<b>Marker Size:&nbsp;&nbsp;</b>"""
        )
        marker_size_scale_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        marker_size_scale_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # Marker alpha controls
        marker_alpha_scale_div = bokeh.models.Div(text="""<b>Marker Alpha:&nbsp;</b>""")
        marker_alpha_scale_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        marker_alpha_scale_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # Marker scale controls
        def increase_marker_size_scale(attr):
            self.marker_size_scale *= 1.5
            parent.trigger_update()

        marker_size_scale_inc.on_click(increase_marker_size_scale)

        def decrease_marker_size_scale(attr):
            self.marker_size_scale /= 1.5
            parent.trigger_update()

        marker_size_scale_dec.on_click(decrease_marker_size_scale)

        # Marker alpha controls
        def increase_marker_alpha_scale(attr):
            self.marker_alpha_scale *= 1.5
            parent.trigger_update()

        marker_alpha_scale_inc.on_click(increase_marker_alpha_scale)

        def decrease_marker_alpha_scale(attr):
            self.marker_alpha_scale /= 1.5
            parent.trigger_update()

        marker_alpha_scale_dec.on_click(decrease_marker_alpha_scale)

        # Reset button:
        reset_button = bokeh.models.Button(label="Reset", button_type="success")

        def reset_button_action(attr):
            self.reset_markers()
            parent.trigger_update()

        reset_button.on_click(reset_button_action)

        c1 = column(
            row(marker_size_scale_div, marker_size_scale_dec, marker_size_scale_inc),
            row(
                marker_alpha_scale_div,
                marker_alpha_scale_dec,
                marker_alpha_scale_inc,
            ),
            width=200,
            margin=(0, 10),
            stylesheets=[
                styles.darkstyle,
                styles.typekit_stylesheet,
            ],
        )
        c2 = column(
            reset_button,
            width=200,
            margin=(0, 10),
        )

        return row(
            c1,
            c2,
        )

    def make_styles_layout(
        self,
        styles=None,
        parent=None,
    ):
        # Allow users to adjust the factor that makes "selected" colors lighter/darker
        # than default colors:
        selected_color_factor_div = bokeh.models.Div(
            text="""<b>Selected Color Factor:&nbsp;&nbsp;</b>""",
            styles={"text-align": "left"},
        )
        selected_color_factor_spinner = bokeh.models.Spinner(
            title="Factor",
            description=(
                "Use to adjust the color of selected atoms to be darker/lighter "
                "than default colors. Numbers less than 0 make the color darker, "
                "greater than 0 make it lighter."
            ),
            value=self.selected_color_factor,
            format="0.0",
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            **dict(width=80, low=-1, high=1, step=0.1),
        )

        # Component styling widgets
        pickers = []
        radius_spinners_by_name = dict()
        pickers_by_name = dict()
        line_color_pickers_by_name = dict()
        line_dash_selects_by_name = dict()
        line_width_spinners_by_name = dict()

        def make_radius_update_callback(component_name):
            def update_radius(attr, old, new):
                if self._update_disabled:
                    return
                self._update_disabled = True
                self.component_params[component_name]["radius_pm"] = new
                if not component_name.endswith("_sel"):
                    selected_name = f"{component_name}_sel"
                    self.component_params[selected_name]["radius_pm"] = new
                self._update_disabled = False
                if parent:
                    parent.trigger_update()

            return update_radius

        # Callback factory functions
        def make_color_update_callback(component_name):
            def update_color(attr, old, new):
                if self._update_disabled:
                    return

                new_adjusted = adjust_color(
                    color=new,
                    factor=self.selected_color_factor,
                )
                selected_name = f"{component_name}_sel"

                self._update_disabled = True
                self.component_params[component_name]["color"] = new

                if not component_name.endswith("_sel"):
                    pickers_by_name[selected_name].color = new_adjusted
                    self.component_params[selected_name]["color"] = new_adjusted
                self._update_disabled = False
                if parent:
                    parent.trigger_update()

            return update_color

        def make_alpha_update_callback(component_name):
            def update_alpha(attr, old, new):
                if self._update_disabled:
                    return

                self._update_disabled = True
                self.component_params[component_name]["alpha"] = new
                self._update_disabled = False
                if parent:
                    parent.trigger_update()

            return update_alpha

        def make_line_dash_update_callback(component_name):
            def update_line_dash(attr, old, new):
                if self._update_disabled:
                    return

                self._update_disabled = True
                self.component_params[component_name]["line_dash"] = new
                self._update_disabled = False
                if parent:
                    parent.trigger_update()

            return update_line_dash

        def make_line_color_update_callback(component_name):
            def update_line_color(attr, old, new):
                if self._update_disabled:
                    return

                self._update_disabled = True
                self.component_params[component_name]["line_color"] = new
                self._update_disabled = False
                if parent:
                    parent.trigger_update()

            return update_line_color

        def make_line_width_update_callback(component_name):
            def update_line_width(attr, old, new):
                if self._update_disabled:
                    return

                self._update_disabled = True
                self.component_params[component_name]["line_width"] = new
                self._update_disabled = False
                if parent:
                    parent.trigger_update()

            return update_line_width

        def update_selected_color_factor(attr, old, new):
            self.selected_color_factor = new
            self._update_disabled = True

            for comp, params in self.component_params.items():
                if comp.endswith("_sel"):
                    continue
                default_color = params.get("color", "#FFFFFF")
                adjusted_color = adjust_color(
                    color=default_color,
                    factor=self.selected_color_factor,
                )
                selected_name = f"{comp}_sel"
                if selected_name in self.component_params:
                    self.component_params[selected_name]["color"] = adjusted_color
                    if selected_name in pickers_by_name:
                        pickers_by_name[selected_name].color = adjusted_color

            self._update_disabled = False
            if parent:
                parent.trigger_update()

        selected_color_factor_spinner.on_change("value", update_selected_color_factor)

        # Create widgets for each component
        for comp, params in self.component_params.items():
            if comp.endswith("_sel"):
                continue

            row_items = []

            # Create label div
            label_div = bokeh.models.Div(
                text=f"<b>{comp}:</b>",
                width=40,
                margin=(25, 5, 0, 0),
                align="center",  # Center align vertically
                styles={"text-align": "right"},
            )
            row_items.append(label_div)

            # === SECTION 0: Radius ===

            # Radius spinner
            radius_spinner = bokeh.models.Spinner(
                title="Radius (pm)",
                value=params.get("radius_pm", 100.0),
                width=80,
                low=0.0,
                high=None,
                step=1.0,
                format="0.0",
                align="end",
                stylesheets=[styles.dark_bk_input_style] if styles else [],
            )
            radius_spinners_by_name[comp] = radius_spinner
            radius_spinner.on_change("value", make_radius_update_callback(comp))
            row_items.append(radius_spinner)

            # === SECTION 1: Default Fill Styles ===

            # Fill Div:
            fill_div = bokeh.models.Div(
                text="<b>Fill:</b>",
                width=50,
                margin=(0, 0, 0, 5),
                align="end",
                styles={"text-align": "left"},
            )

            # Default fill color picker
            color = params.get("color", "#FFFFFF")
            color_picker = bokeh.models.ColorPicker(
                title="Color",
                color=color,
                width=60,
                height=30,
                stylesheets=[styles.dark_bk_input_style] if styles else [],
            )
            pickers_by_name[comp] = color_picker
            color_picker.on_change("color", make_color_update_callback(comp))

            # Default alpha spinner
            alpha_spinner = bokeh.models.Spinner(
                title="Alpha",
                value=params.get("alpha", 0.8),
                width=80,
                low=0.0,
                high=1.0,
                step=0.1,
                format="0.0",
                stylesheets=[styles.dark_bk_input_style] if styles else [],
            )
            alpha_spinner.on_change("value", make_alpha_update_callback(comp))

            fill_widgets = column(
                row(fill_div),
                row(color_picker, alpha_spinner),
                margin=(0, 0, 0, 0),
            )

            row_items.append(fill_widgets)

            # === SECTION 2: Default Line Styles ===

            # Line Div:
            line_div = bokeh.models.Div(
                text="<b>Line:</b>",
                width=50,
                margin=(0, 0, 0, 5),
                align="end",
                styles={"text-align": "left"},
            )

            # Default line style selector
            line_dash_options = ["solid", "dashed", "dotted", "dotdash", "dashdot"]
            line_dash_select = bokeh.models.Select(
                title="Style",
                value=params.get("line_dash", "solid"),
                options=line_dash_options,
                width=100,
                stylesheets=[styles.dark_bk_input_style] if styles else [],
            )
            line_dash_selects_by_name[comp] = line_dash_select
            line_dash_select.on_change("value", make_line_dash_update_callback(comp))

            # Default line color picker
            line_color = params.get("line_color", "#000000")
            line_color_picker = bokeh.models.ColorPicker(
                title="Color",
                color=line_color,
                width=60,
                height=30,
                stylesheets=[styles.dark_bk_input_style] if styles else [],
            )
            line_color_pickers_by_name[comp] = line_color_picker
            line_color_picker.on_change("color", make_line_color_update_callback(comp))

            # Default line width spinner
            line_width_spinner = bokeh.models.Spinner(
                title="Width",
                value=params.get("line_width", 1.0),
                width=80,
                low=0.0,
                high=10.0,
                step=0.25,
                format="0.00",
                stylesheets=[styles.dark_bk_input_style] if styles else [],
            )
            line_width_spinners_by_name[comp] = line_width_spinner
            line_width_spinner.on_change("value", make_line_width_update_callback(comp))

            line_widgets = column(
                row(line_div),
                row(line_dash_select, line_color_picker, line_width_spinner),
                margin=(0, 0, 0, 0),
            )
            row_items.append(line_widgets)

            # === SECTION 3 & 4: Selected Fill and Line Styles ===

            if f"{comp}_sel" in self.component_params:
                sel_params = self.component_params[f"{comp}_sel"]

                # === SECTION 3: Selected Fill Styles ===

                # Selected Fill Div:
                sel_fill_div = bokeh.models.Div(
                    text="<b>Selected Fill:</b>",
                    width=140,
                    margin=(0, 0, 0, 5),
                    align="end",
                    styles={"text-align": "left"},
                )

                # Selected fill color picker
                sel_color = sel_params.get("color", "#FF0000")
                sel_color_picker = bokeh.models.ColorPicker(
                    title="Color",
                    color=sel_color,
                    width=60,
                    height=30,
                    stylesheets=[styles.dark_bk_input_style] if styles else [],
                )
                pickers_by_name[f"{comp}_sel"] = sel_color_picker
                sel_color_picker.on_change(
                    "color", make_color_update_callback(f"{comp}_sel")
                )

                # Selected alpha spinner
                sel_alpha_spinner = bokeh.models.Spinner(
                    title="Alpha",
                    value=sel_params.get("alpha", 0.8),
                    width=80,
                    low=0.0,
                    high=1.0,
                    step=0.1,
                    format="0.0",
                    stylesheets=[styles.dark_bk_input_style] if styles else [],
                )
                sel_alpha_spinner.on_change(
                    "value", make_alpha_update_callback(f"{comp}_sel")
                )

                sel_fill_widgets = column(
                    row(sel_fill_div),
                    row(sel_color_picker, sel_alpha_spinner),
                    margin=(0, 0, 0, 0),
                )
                row_items.append(sel_fill_widgets)

                # === SECTION 4: Selected Line Styles ===

                # Selected Line Div:
                sel_line_div = bokeh.models.Div(
                    text="<b>Selected Line:</b>",
                    width=140,
                    margin=(0, 0, 0, 5),
                    align="end",
                    styles={"text-align": "left"},
                )

                # Selected line style selector
                sel_line_dash_select = bokeh.models.Select(
                    title="Style",
                    value=sel_params.get("line_dash", "solid"),
                    options=line_dash_options,
                    width=100,
                    stylesheets=[styles.dark_bk_input_style] if styles else [],
                )
                line_dash_selects_by_name[f"{comp}_sel"] = sel_line_dash_select
                sel_line_dash_select.on_change(
                    "value", make_line_dash_update_callback(f"{comp}_sel")
                )

                # Selected line color picker
                sel_line_color = sel_params.get("line_color", "#000000")
                sel_line_color_picker = bokeh.models.ColorPicker(
                    title="Color",
                    color=sel_line_color,
                    width=60,
                    height=30,
                    stylesheets=[styles.dark_bk_input_style] if styles else [],
                )
                line_color_pickers_by_name[f"{comp}_sel"] = sel_line_color_picker
                sel_line_color_picker.on_change(
                    "color", make_line_color_update_callback(f"{comp}_sel")
                )

                # Selected line width spinner
                sel_line_width_spinner = bokeh.models.Spinner(
                    title="Width",
                    value=sel_params.get("line_width", 1.0),
                    width=80,
                    low=0.0,
                    high=10.0,
                    step=0.25,
                    format="0.00",
                    stylesheets=[styles.dark_bk_input_style] if styles else [],
                )
                line_width_spinners_by_name[f"{comp}_sel"] = sel_line_width_spinner
                sel_line_width_spinner.on_change(
                    "value", make_line_width_update_callback(f"{comp}_sel")
                )

                sel_line_widgets = column(
                    row(sel_line_div),
                    row(
                        sel_line_dash_select,
                        sel_line_color_picker,
                        sel_line_width_spinner,
                    ),
                    margin=(0, 0, 0, 0),
                )
                row_items.append(sel_line_widgets)

            # Add label and all widgets as a row
            picker_row = row(*row_items, margin=(10, 10))
            pickers.append(picker_row)

            # end component styler loop

        layout = column(
            row(
                selected_color_factor_div,
                selected_color_factor_spinner,
                width=300,
                margin=(0, 0, 0, 0),
            ),
            bokeh.models.Div(
                text="""<b>Component Styles:</b>""",
                width=300,
                styles={"text-align": "left"},
            ),
            *pickers,
            stylesheets=[
                DashboardStyles().darkstyle,
                DashboardStyles().typekit_stylesheet,
            ],
        )

        # Save styles widgets:
        self._widgets["styles"] = dict()
        self._widgets["styles"]["radius_spinners_by_name"] = radius_spinners_by_name
        self._widgets["styles"][
            "selected_color_factor_spinner"
        ] = selected_color_factor_spinner
        self._widgets["styles"]["pickers_by_name"] = pickers_by_name
        self._widgets["styles"][
            "line_color_pickers_by_name"
        ] = line_color_pickers_by_name
        self._widgets["styles"]["line_dash_selects_by_name"] = line_dash_selects_by_name
        self._widgets["styles"][
            "line_width_spinners_by_name"
        ] = line_width_spinners_by_name

        return layout

    def make_projaxes_control_layout(
        self,
        styles=None,
        parent=None,
    ):
        # Projection rotation angle controls
        projection_rotation_angle_div = bokeh.models.Div(
            text="""<b>Rotation Angle:</b>"""
        )
        projection_rotation_angle_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        projection_rotation_angle_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # Cabinet rotate controls
        projection_rotate_b1_div = bokeh.models.Div(text="""<b>Rotate b1:</b>""")
        projection_rotate_b1_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        projection_rotate_b1_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        projection_rotate_b2_div = bokeh.models.Div(text="""<b>Rotate b2:</b>""")
        projection_rotate_b2_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        projection_rotate_b2_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        projection_rotate_b3_div = bokeh.models.Div(text="""<b>Rotate b3:</b>""")
        projection_rotate_b3_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        projection_rotate_b3_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # projection view axes input
        projaxes_input = ProjectionAxesInput(
            view_control=self,
            styles=styles,
            parent=parent,
        )

        # Reset button:
        reset_button = bokeh.models.Button(label="Reset", button_type="success")

        # --- Callbacks ---

        def reset_button_action(attr):
            self.reset_projection_view()
            parent.trigger_update()
            projaxes_input._update_view_basis()

        reset_button.on_click(reset_button_action)

        # Cabinet rotation angle controls
        def increase_projection_rotation_angle(attr):
            self.projection_rotation_angle += 1.0
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotation_angle_inc.on_click(increase_projection_rotation_angle)

        def decrease_projection_rotation_angle(attr):
            if self.projection_rotation_angle <= 1.0:
                return
            self.projection_rotation_angle -= 1.0
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotation_angle_dec.on_click(decrease_projection_rotation_angle)

        # Cabinet rotate controls
        def rotate_b1_inc(attr):
            self.rotate_projection_view_basis(
                np.array([1.0, 0.0, 0.0]),
                parent.projection_view.projection_view.view_basis,
                self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b1_inc.on_click(rotate_b1_inc)

        def rotate_b1_dec(attr):
            self.rotate_projection_view_basis(
                np.array([1.0, 0.0, 0.0]),
                parent.projection_view.projection_view.view_basis,
                -self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b1_dec.on_click(rotate_b1_dec)

        def rotate_b2_inc(attr):
            self.rotate_projection_view_basis(
                np.array([0.0, 1.0, 0.0]),
                parent.projection_view.projection_view.view_basis,
                self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b2_inc.on_click(rotate_b2_inc)

        def rotate_b2_dec(attr):
            self.rotate_projection_view_basis(
                np.array([0.0, 1.0, 0.0]),
                parent.projection_view.projection_view.view_basis,
                -self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b2_dec.on_click(rotate_b2_dec)

        def rotate_b3_inc(attr):
            self.rotate_projection_view_basis(
                np.array([0.0, 0.0, 1.0]),
                parent.projection_view.projection_view.view_basis,
                self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b3_inc.on_click(rotate_b3_inc)

        def rotate_b3_dec(attr):
            self.rotate_projection_view_basis(
                np.array([0.0, 0.0, 1.0]),
                parent.projection_view.projection_view.view_basis,
                -self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b3_dec.on_click(rotate_b3_dec)

        # Fix axes range switch

        fix_axes_range_switch = bokeh.models.Switch(
            label="Fix axes range",
            active=False,
        )

        def fix_axes_range_switch_action(attr, old, new):
            from bokeh.models import DataRange1d, Range1d

            plot = parent.projection_view.projection_view.plot

            if new is False:
                plot.x_range = DataRange1d()
                plot.y_range = DataRange1d()
            else:
                # Get current range values
                x_start = plot.x_range.start
                x_end = plot.x_range.end
                y_start = plot.y_range.start
                y_end = plot.y_range.end

                plot.x_range = Range1d(start=x_start, end=x_end)
                plot.y_range = Range1d(start=y_start, end=y_end)
            parent.trigger_update()

        fix_axes_range_switch.on_change("active", fix_axes_range_switch_action)

        # --- Layout ---

        c1b = projaxes_input.layout
        c2 = column(
            row(
                projection_rotation_angle_div,
                projection_rotation_angle_dec,
                projection_rotation_angle_inc,
            ),
            row(
                projection_rotate_b1_div,
                projection_rotate_b1_dec,
                projection_rotate_b1_inc,
            ),
            row(
                projection_rotate_b2_div,
                projection_rotate_b2_dec,
                projection_rotate_b2_inc,
            ),
            row(
                projection_rotate_b3_div,
                projection_rotate_b3_dec,
                projection_rotate_b3_inc,
            ),
            fix_axes_range_switch,
            width=200,
            margin=(0, 10),
        )
        c3 = column(
            reset_button,
            width=200,
            margin=(0, 10),
        )
        layout = row(
            c1b,
            c2,
            c3,
            stylesheets=[
                styles.darkstyle,
                styles.typekit_stylesheet,
            ],
        )

        # Save projection axes:
        self._projaxes_input = projaxes_input

        return layout

    def make_projection_control_layout(
        self,
        styles=None,
        parent=None,
    ):
        projection_type_div = bokeh.models.Div(text="""<b>Projection Type:</b>""")
        projection_type_select = bokeh.models.Select(
            value=self.projection.label,
            options=["Single point", "Isometric", "Cabinet"],
            stylesheets=[styles.dark_bk_input_style],
            width=200,
        )

        ### Cabinet controls ###

        # Cabinet scale controls
        cabinet_scale_div = bokeh.models.Div(text="""<b>Cabinet Scale:</b>""")
        cabinet_scale_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        cabinet_scale_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # Cabinet angle controls
        cabinet_angle_div = bokeh.models.Div(text="""<b>Cabinet Angle:</b>""")
        cabinet_angle_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        cabinet_angle_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # Cabinet scale controls
        def increase_cabinet_scale(attr):
            self.projection.scale *= 1.5
            parent.trigger_update()

        cabinet_scale_inc.on_click(increase_cabinet_scale)

        def decrease_cabinet_scale(attr):
            self.projection.scale /= 1.5
            parent.trigger_update()

        cabinet_scale_dec.on_click(decrease_cabinet_scale)

        # Cabinet angle controls
        def increase_cabinet_angle(attr):
            self.projection.angle += math.pi / 36.0
            parent.trigger_update()

        cabinet_angle_inc.on_click(increase_cabinet_angle)

        def decrease_cabinet_angle(attr):
            self.projection.angle -= math.pi / 36.0
            parent.trigger_update()

        cabinet_angle_dec.on_click(decrease_cabinet_angle)

        cabinet_control_layout = column(
            row(cabinet_scale_div, cabinet_scale_dec, cabinet_scale_inc),
            row(cabinet_angle_div, cabinet_angle_dec, cabinet_angle_inc),
            width=200,
            margin=(0, 10),
            visible=isinstance(self.projection, CabinetProjection),
        )

        ### Single point controls ###

        # Projection viewer distance
        viewer_distance_div = bokeh.models.Div(text="""<b>Viewer Distance:</b>""")
        viewer_distance_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        viewer_distance_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # Projection plane offset
        plane_offset_div = bokeh.models.Div(text="""<b>Plane Offset:</b>""")
        plane_offset_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        plane_offset_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        self.plane_offset_step_size = 5.0

        # Callbacks:
        def increase_viewer_distance(attr):
            if isinstance(self.projection, SinglePointProjection):
                self.projection.viewer_distance *= 1.5
                parent.trigger_update()

        viewer_distance_inc.on_click(increase_viewer_distance)

        def decrease_viewer_distance(attr):
            if isinstance(self.projection, SinglePointProjection):
                self.projection.viewer_distance /= 1.5
                parent.trigger_update()

        viewer_distance_dec.on_click(decrease_viewer_distance)

        def increase_plane_offset(attr):
            if isinstance(self.projection, SinglePointProjection):
                self.projection.plane_offset += self.plane_offset_step_size
                parent.trigger_update()

        plane_offset_inc.on_click(increase_plane_offset)

        def decrease_plane_offset(attr):
            if isinstance(self.projection, SinglePointProjection):
                self.projection.plane_offset -= self.plane_offset_step_size
                parent.trigger_update()

        plane_offset_dec.on_click(decrease_plane_offset)

        singlepoint_control_layout = column(
            row(viewer_distance_div, viewer_distance_dec, viewer_distance_inc),
            row(plane_offset_div, plane_offset_dec, plane_offset_inc),
            width=200,
            margin=(0, 10),
            visible=isinstance(self.projection, SinglePointProjection),
        )

        ### Isometric controls ###

        # (No additional controls for isometric projection)

        isometric_control_layout = column(
            bokeh.models.Div(text=""),
            width=200,
            margin=(0, 10),
            visible=isinstance(self.projection, IsometricProjection),
        )

        ### Shared controls ###

        def update_projection_type(attr, old, new):
            if new == "Cabinet" and not isinstance(self.projection, CabinetProjection):
                self.projection = CabinetProjection()
                cabinet_control_layout.visible = True
                singlepoint_control_layout.visible = False
                isometric_control_layout.visible = False
                parent.trigger_update()
            elif new == "Single point" and not isinstance(
                self.projection, SinglePointProjection
            ):
                self.projection = SinglePointProjection()
                cabinet_control_layout.visible = False
                singlepoint_control_layout.visible = True
                isometric_control_layout.visible = False
                parent.trigger_update()
            elif new == "Isometric" and not isinstance(
                self.projection, IsometricProjection
            ):
                self.projection = IsometricProjection()
                cabinet_control_layout.visible = False
                singlepoint_control_layout.visible = False
                isometric_control_layout.visible = True
                parent.trigger_update()

        projection_type_select.on_change("value", update_projection_type)

        # Reset button:
        reset_button = bokeh.models.Button(label="Reset", button_type="success")

        def reset_button_action(attr):
            self.plane_offset_step_size = 5.0
            if isinstance(self.projection, CabinetProjection):
                self.projection = CabinetProjection()
            elif isinstance(self.projection, SinglePointProjection):
                self.projection = SinglePointProjection()
            elif isinstance(self.projection, IsometricProjection):
                self.projection = IsometricProjection()
            parent.trigger_update()

        reset_button.on_click(reset_button_action)

        layout = row(
            column(
                projection_type_div,
                projection_type_select,
                width=200,
                margin=(0, 10),
            ),
            cabinet_control_layout,
            singlepoint_control_layout,
            reset_button,
            stylesheets=[
                styles.darkstyle,
                styles.typekit_stylesheet,
            ],
        )

        return layout

    # Layout for specifying layout_type, width, and height:
    def make_layout_control_layout(
        self,
        styles=None,
        parent=None,
    ):
        layout_type_select = bokeh.models.Select(
            title="Layout Type",
            value=self.layout_type,
            options=["multiview", "singleview"],
            stylesheets=[styles.dark_bk_input_style],
            width=200,
        )

        singleview_div = bokeh.models.Div(text="""<b>Single View:</b>""")

        singleview_width_spinner = bokeh.models.Spinner(
            title="Figure width",
            value=self.singleview_figure_params["width"],
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            **dict(width=80, low=100, high=2000, step=50),
        )

        singleview_height_spinner = bokeh.models.Spinner(
            title="Figure height",
            value=self.singleview_figure_params["height"],
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            **dict(width=80, low=100, high=2000, step=50),
        )

        multivew_div = bokeh.models.Div(text="""<b>Multi View:</b>""")

        multiview_width_spinner = bokeh.models.Spinner(
            title="Figure width",
            value=self.multiview_figure_params["width"],
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            **dict(width=80, low=100, high=2000, step=50),
        )

        multiview_height_spinner = bokeh.models.Spinner(
            title="Figure height",
            value=self.multiview_figure_params["height"],
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            **dict(width=80, low=100, high=2000, step=50),
        )

        # Callbacks
        def update_layout_type(attr, old, new):
            if self._update_disabled:
                return

            self._update_disabled = True
            self.layout_type = new
            self._update_disabled = False
            parent.projection_view.update_layout_type()
            parent.trigger_update()
            parent.projection_view.update_layout()

        layout_type_select.on_change("value", update_layout_type)

        def update_singleview_width(attr, old, new):
            if self._update_disabled:
                return

            self._update_disabled = True
            self.singleview_figure_params["width"] = new
            self._update_disabled = False
            parent.projection_view.update_layout()
            parent.trigger_update()

        singleview_width_spinner.on_change("value", update_singleview_width)

        def update_singleview_height(attr, old, new):
            if self._update_disabled:
                return

            self._update_disabled = True
            self.singleview_figure_params["height"] = new
            self._update_disabled = False
            parent.projection_view.update_layout()
            parent.trigger_update()

        singleview_height_spinner.on_change("value", update_singleview_height)

        def update_multiview_width(attr, old, new):
            if self._update_disabled:
                return

            self._update_disabled = True
            self.multiview_figure_params["width"] = new
            self._update_disabled = False
            parent.projection_view.update_layout()
            parent.trigger_update()

        multiview_width_spinner.on_change("value", update_multiview_width)

        def update_multiview_height(attr, old, new):
            if self._update_disabled:
                return

            self._update_disabled = True
            self.multiview_figure_params["height"] = new
            self._update_disabled = False
            parent.projection_view.update_layout()
            parent.trigger_update()

        multiview_height_spinner.on_change("value", update_multiview_height)

        self._widgets["layout"] = dict()
        self._widgets["layout"]["layout_type_select"] = layout_type_select
        self._widgets["layout"]["multiview_width_spinner"] = multiview_width_spinner
        self._widgets["layout"]["multiview_height_spinner"] = multiview_height_spinner
        self._widgets["layout"]["singleview_width_spinner"] = singleview_width_spinner
        self._widgets["layout"]["singleview_height_spinner"] = singleview_height_spinner

        layout = column(
            row(
                column(
                    layout_type_select,
                    width=240,
                    margin=(0, 10),
                ),
                column(
                    multivew_div,
                    multiview_height_spinner,
                    multiview_width_spinner,
                    width=150,
                    margin=(0, 10),
                ),
                column(
                    singleview_div,
                    singleview_height_spinner,
                    singleview_width_spinner,
                    width=150,
                    margin=(0, 10),
                ),
            ),
            stylesheets=[
                styles.darkstyle,
                styles.typekit_stylesheet,
            ],
        )

        self._widgets["layout"] = dict()
        self._widgets["layout"]["layout_type_select"] = layout_type_select
        self._widgets["layout"]["multiview_width_spinner"] = multiview_width_spinner
        self._widgets["layout"]["multiview_height_spinner"] = multiview_height_spinner
        self._widgets["layout"]["singleview_width_spinner"] = singleview_width_spinner
        self._widgets["layout"]["singleview_height_spinner"] = singleview_height_spinner

        return layout

    def make_misc_control_layout(
        self,
        styles=None,
        parent=None,
    ):
        # Set grid lines visibility
        grid_lines_switch = bokeh.models.Switch(
            label="Show Grid Lines",
            active=self.misc_show_grid_lines,
        )

        # Make axes, labels, title, background, etc. transparent
        transparency_mode_switch = bokeh.models.Switch(
            label="Transparency mode",
            active=self.misc_transparency_mode,
        )

        def grid_lines_switch_action(attr, old, new):
            if self._update_disabled:
                return

            self._update_disabled = True
            self.misc_show_grid_lines = new
            parent.projection_view.set_grid_visibility(new)
            self._update_disabled = False

        grid_lines_switch.on_change("active", grid_lines_switch_action)

        def transparency_mode_switch_action(attr, old, new):
            if self._update_disabled:
                return

            self._update_disabled = True
            self.misc_transparency_mode = new
            parent.projection_view.set_transparency_mode(new)
            self._update_disabled = False

        transparency_mode_switch.on_change("active", transparency_mode_switch_action)

        self._widgets["misc"] = dict()
        self._widgets["misc"]["grid_lines_switch"] = grid_lines_switch
        self._widgets["misc"]["transparency_mode_switch"] = transparency_mode_switch

        layout = column(
            grid_lines_switch,
            transparency_mode_switch,
            width=200,
            margin=(0, 10),
            stylesheets=[
                styles.darkstyle,
                styles.typekit_stylesheet,
            ],
        )

        return layout

    def make_state_control_layout(
        self,
        views_dir: pathlib.Path,
        styles=None,
        parent=None,
    ):
        """
        Create a layout for managing saved view states.

        Parameters
        ----------
        views_dir : pathlib.Path
            Directory where view states are saved.
        styles : DashboardStyles, optional
            Provides styling for the layout.
        parent : typing.Any, optional
            The parent Dashboard object.

        Returns
        -------
        layout : bokeh.layouts.column
            A Bokeh layout for managing saved view states.
        """

        # Save default state if not already present:
        views_dir.mkdir(parents=True, exist_ok=True)
        default_state_path = views_dir / "default.json"
        if not default_state_path.exists():
            with open(default_state_path, "w") as f:
                f.write(xtal.pretty_json(self.get_state()))

        # Dropdown to select saved states
        options = [str(f.stem) for f in views_dir.glob("*.json")]
        options += ["(current)"]
        saved_states_select = bokeh.models.Select(
            title="Load a saved state",
            options=options,
            value="(current)",
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            width=300,
        )

        # Input box to name the current state
        state_name_input = bokeh.models.TextInput(
            title="Save current state as",
            placeholder="Enter a name for the current state",
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            width=300,
        )

        # Save button
        save_button = bokeh.models.Button(
            label="Save",
            button_type="success",
            stylesheets=[styles.dark_bk_input_style] if styles else [],
        )

        # Input box to name a state to delete
        delete_state_name_input = bokeh.models.TextInput(
            title="State to delete",
            placeholder="Enter the name of a state to delete",
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            width=300,
        )

        # Delete button
        delete_button = bokeh.models.Button(
            label="Delete",
            button_type="danger",
            stylesheets=[styles.dark_bk_input_style] if styles else [],
        )

        # Message div
        message_div = bokeh.models.Div(
            text="", width=600, stylesheets=[styles.darkstyle] if styles else []
        )

        # Callbacks
        def save_state():
            if self._update_disabled:
                return

            name = state_name_input.value.strip()

            if not name:
                message_div.text = (
                    "<b style='color: red;'>Please enter a valid name.</b>"
                )
                return

            self._update_disabled = True
            views_dir.mkdir(parents=True, exist_ok=True)
            name = state_name_input.value.strip()
            state_path = views_dir / f"{name}.json"
            with open(state_path, "w") as f:
                f.write(xtal.pretty_json(self.get_state()))
            options = [str(f.stem) for f in views_dir.glob("*.json")]
            options += ["(current)"]
            saved_states_select.options = options
            saved_states_select.value = "(current)"

            state_name_input.value = ""
            delete_state_name_input.value = ""
            message_div.text = f"<b>State '{name}' saved.</b>"

            self._update_disabled = False

        def delete_state():
            if self._update_disabled:
                return

            name = delete_state_name_input.value.strip()
            options = [str(f.stem) for f in views_dir.glob("*.json")]
            options += ["(current)"]

            if name not in options:
                message_div.text = (
                    "<b style='color: red;'>"
                    "Please enter a valid state name to delete."
                    "</b>"
                )
                return

            self._update_disabled = True
            state_path = views_dir / f"{name}.json"
            if state_path.exists():
                state_path.unlink()

            options = [str(f.stem) for f in views_dir.glob("*.json")]
            options += ["(current)"]

            saved_states_select.options = [
                str(f.stem) for f in views_dir.glob("*.json")
            ]
            saved_states_select.value = "(current)"

            state_name_input.value = ""
            delete_state_name_input.value = ""
            message_div.text = f"<b>State '{name}' deleted.</b>"

            self._update_disabled = False

        def load_state(attr, old, new):
            if self._update_disabled:
                return
            if not new:
                return
            state_path = views_dir / f"{new}.json"
            if not state_path.exists():
                return
            self._update_disabled = True
            with open(state_path, "r") as f:
                self.set_state(json.load(f))

            saved_states_select.value = "(current)"
            state_name_input.value = ""
            delete_state_name_input.value = ""
            message_div.text = f"<b>State '{new}' loaded.</b>"

            self._update_disabled = False

        # Attach callbacks
        save_button.on_click(save_state)
        delete_button.on_click(delete_state)
        saved_states_select.on_change("value", load_state)

        # Layout
        layout = column(
            saved_states_select,
            state_name_input,
            save_button,
            delete_state_name_input,
            delete_button,
            message_div,
            stylesheets=(
                [styles.darkstyle, styles.typekit_stylesheet] if styles else []
            ),
            width=350,
        )
        return layout

    def make_controls_tabs_layout(
        self,
        select_control_layout: typing.Optional[typing.Any],
        styles: DashboardStyles,
        parent: typing.Any,
        views_dir: typing.Optional[pathlib.Path] = None,
    ):
        """

        Parameters
        ----------
        select_control_layout: typing.Optional[typing.Any]
            If not None, a Bokeh layout, like a Column, to add as a "Select" tab.
        styles: DashboardStyles
            Provides styling
        parent: typing.Any
            The parent Dashboard
        views_dir : typing.Optional[pathlib.Path] = None
            Directory where view states are saved. If provided, a "State" tab will be
            added to manage saved view states.

        Returns
        -------
        layout: bokeh.models.Tabs
            A Bokeh Tabs layout with view controls
        """
        self.parent = parent

        images_control_layout = self.make_images_control_layout(
            styles=styles,
            parent=parent,
        )

        markers_control_layout = self.make_markers_control_layout(
            styles=styles,
            parent=parent,
        )

        styles_control_layout = self.make_styles_layout(
            styles=styles,
            parent=parent,
        )

        projaxes_control_layout = self.make_projaxes_control_layout(
            styles=styles,
            parent=parent,
        )

        projection_control_layout = self.make_projection_control_layout(
            styles=styles,
            parent=parent,
        )

        layout_control_layout = self.make_layout_control_layout(
            styles=styles,
            parent=parent,
        )

        misc_control_layout = self.make_misc_control_layout(
            styles=styles,
            parent=parent,
        )

        tabs = []
        if select_control_layout:
            tabs.append(
                bokeh.models.TabPanel(child=select_control_layout, title="Select")
            )
        tabs += [
            bokeh.models.TabPanel(child=images_control_layout, title="Supercell"),
            bokeh.models.TabPanel(child=markers_control_layout, title="Markers"),
            bokeh.models.TabPanel(child=styles_control_layout, title="Styles"),
            bokeh.models.TabPanel(
                child=projaxes_control_layout, title="Projection Axes"
            ),
            bokeh.models.TabPanel(
                child=projection_control_layout, title="Projection Type"
            ),
            bokeh.models.TabPanel(child=layout_control_layout, title="Layout"),
            bokeh.models.TabPanel(child=misc_control_layout, title="Misc"),
        ]

        if views_dir is not None:
            state_control_layout = self.make_state_control_layout(
                views_dir=views_dir,
                styles=styles,
                parent=parent,
            )
            tabs.append(
                bokeh.models.TabPanel(child=state_control_layout, title="State")
            )

        tabs_layout = bokeh.models.Tabs(
            tabs=tabs,
            stylesheets=[
                styles.darkstyle,
                styles.typekit_stylesheet,
            ],
        )
        tabs_layout.visible = False

        toggle_button = bokeh.models.Switch(label="Settings", active=False)

        # CustomJS to toggle visibility
        toggle_button.js_on_change(
            "active",
            bokeh.models.CustomJS(
                args=dict(tabs_layout=tabs_layout),
                code="""
            tabs_layout.visible = cb_obj.active;
        """,
            ),
        )

        control_layout = column(
            row(
                toggle_button,
                height=30,
            ),
            tabs_layout,
            margin=(0, 20),  # top/bottom, left/right
        )

        # control_layout = column(
        #     images_control_layout,
        #     markers_control_layout,
        #     projaxes_control_layout,
        #     stylesheets=[
        #         styles.darkstyle,
        #         styles.typekit_stylesheet,
        #     ],
        # )

        return control_layout
