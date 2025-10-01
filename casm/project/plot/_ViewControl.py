import copy
import math
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
    ViewAtomicStructure,
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
        projection_view: ViewAtomicStructure = None,
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
        projection_view: ViewAtomicStructure
            The projection view.

        """
        self.view_control = view_control
        self.styles = styles
        self.parent = parent
        self.projection_view = projection_view

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
        # Must include "color", "size", and "alpha". Additional bokeh plotting
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

        Must include "color", "size", and "alpha". Additional bokeh plotting
        parameters like "line_color" and "line_width" may also be included. The
        same attributes must be present for all components.
        """

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
        self.projection = self._initial_projection

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
            "a_range": self.images_a_range,
            "b_range": self.images_b_range,
            "c_range": self.images_c_range,
            "m_range": self.images_m_range,
            "marker_size_scale": self.marker_size_scale,
            "marker_alpha_scale": self.marker_alpha_scale,
            "selected_color_factor": self.selected_color_factor,
            "component_params": self.component_params,
            "projection": self.projection.to_dict(),
            "projection_v1": self.projection_v1.tolist(),
            "projection_v2": self.projection_v2.tolist(),
        }

    def set_state(
        self,
        state: dict,
    ):
        self.images_a_range = state["a_range"]
        self.images_b_range = state["b_range"]
        self.images_c_range = state["c_range"]
        self.images_m_range = state["m_range"]
        self.selected_color_factor = state["selected_color_factor"]
        self.component_params = state["component_params"]
        self.marker_size_scale = state["marker_size_scale"]
        self.marker_alpha_scale = state["marker_alpha_scale"]
        self.projection = make_projection_from_dict(state["projection"])
        self.projection_v1 = np.array(state["projection_v1"])
        self.projection_v2 = np.array(state["projection_v2"])

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

    def make_colors_layout(
        self,
        styles=None,
        parent=None,
    ):
        # Allow users to adjust the factor that makes "selected" colors lighter/darker
        # than default colors:
        selected_color_factor_div = bokeh.models.Div(
            text="""<b>Selected Color Factor:&nbsp;&nbsp;</b>"""
        )
        selected_color_factor_spinner = bokeh.models.Spinner(
            title="Factor",
            description=(
                "Use to adjust the color of selected atoms to be darker/lighter "
                "than default colors. Numbers less than 0 make the color darker, "
                "greater than 0 make it lighter."
            ),
            value=self.selected_color_factor,
            stylesheets=[styles.dark_bk_input_style] if styles else [],
            **dict(width=80, low=-10, high=10, step=1),
        )

        def update_selected_color_factor(attr, old, new):
            self.selected_color_factor = new / 10.0
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

        # Color pickers for each component
        pickers = []
        pickers_by_name = dict()
        for comp, params in self.component_params.items():
            if comp.endswith("_sel"):
                continue

            row_items = []

            color = params.get("color", "#FFFFFF")

            # Create label div
            label_div = bokeh.models.Div(
                text=f"<b>{comp}:</b>",
                width=40,
                margin=(25, 5, 0, 0),
                align="center",  # Center align vertically
                styles={"text-align": "right"},
            )
            row_items.append(label_div)

            # Create color picker
            color_picker = bokeh.models.ColorPicker(
                title="Default",
                color=color,
                width=60,
                height=30,
                stylesheets=[styles.dark_bk_input_style] if styles else [],
            )
            pickers_by_name[comp] = color_picker

            row_items.append(color_picker)

            # Add callback to update component params and trigger parent update
            def make_color_update_callback(component_name):
                def update_color(attr, old, new):
                    print("new:", new)
                    print("selected_color_factor:", self.selected_color_factor)
                    new_adjusted = adjust_color(
                        color=new,
                        factor=self.selected_color_factor,
                    )
                    print("new_adjusted:", new_adjusted)
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

            color_picker.on_change("color", make_color_update_callback(comp))

            # Create "selected" color picker
            if f"{comp}_sel" in self.component_params:
                sel_color = self.component_params[f"{comp}_sel"].get("color", "#FF0000")
                sel_color_picker = bokeh.models.ColorPicker(
                    title="Selected",
                    color=sel_color,
                    width=60,
                    height=30,
                    stylesheets=[styles.dark_bk_input_style] if styles else [],
                )
                pickers_by_name[f"{comp}_sel"] = sel_color_picker

                sel_color_picker.on_change(
                    "color", make_color_update_callback(f"{comp}_sel")
                )

                row_items.append(sel_color_picker)

            # Add label and picker as a row
            picker_row = row(*row_items, margin=(10, 10))
            pickers.append(picker_row)

        layout = column(
            row(
                selected_color_factor_div,
                selected_color_factor_spinner,
                width=300,
                margin=(0, 10),
            ),
            bokeh.models.Div(text="""<b>Component Colors</b>""", width=300),
            *pickers,
            stylesheets=[
                DashboardStyles().darkstyle,
                DashboardStyles().typekit_stylesheet,
            ],
        )
        return layout

    def make_projaxes_control_layout(
        self,
        styles=None,
        parent=None,
        projection_view: typing.Optional[ViewAtomicStructure] = None,
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
            projection_view=projection_view,
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
                projection_view.view_basis,
                self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b1_inc.on_click(rotate_b1_inc)

        def rotate_b1_dec(attr):
            self.rotate_projection_view_basis(
                np.array([1.0, 0.0, 0.0]),
                projection_view.view_basis,
                -self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b1_dec.on_click(rotate_b1_dec)

        def rotate_b2_inc(attr):
            self.rotate_projection_view_basis(
                np.array([0.0, 1.0, 0.0]),
                projection_view.view_basis,
                self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b2_inc.on_click(rotate_b2_inc)

        def rotate_b2_dec(attr):
            self.rotate_projection_view_basis(
                np.array([0.0, 1.0, 0.0]),
                projection_view.view_basis,
                -self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b2_dec.on_click(rotate_b2_dec)

        def rotate_b3_inc(attr):
            self.rotate_projection_view_basis(
                np.array([0.0, 0.0, 1.0]),
                projection_view.view_basis,
                self.projection_rotation_angle,
            )
            parent.trigger_update()
            projaxes_input._update_view_basis()

        projection_rotate_b3_inc.on_click(rotate_b3_inc)

        def rotate_b3_dec(attr):
            self.rotate_projection_view_basis(
                np.array([0.0, 0.0, 1.0]),
                projection_view.view_basis,
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

            plot = projection_view.plot

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

        return layout

    def make_projection_control_layout(
        self,
        styles=None,
        parent=None,
        projection_view: typing.Optional[ViewAtomicStructure] = None,
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

    def make_controls_tabs_layout(
        self,
        select_control_layout: typing.Optional[typing.Any],
        styles: DashboardStyles,
        parent: typing.Any,
        projection_view: ViewAtomicStructure,
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
        projection_view: ViewAtomicStructure
            The projection view.

        Returns
        -------
        layout: bokeh.models.Tabs
            A Bokeh Tabs layout with view controls
        """
        images_control_layout = self.make_images_control_layout(
            styles=styles,
            parent=parent,
        )

        markers_control_layout = self.make_markers_control_layout(
            styles=styles,
            parent=parent,
        )

        colors_control_layout = self.make_colors_layout(
            styles=styles,
            parent=parent,
        )

        projaxes_control_layout = self.make_projaxes_control_layout(
            styles=styles,
            parent=parent,
            projection_view=projection_view,
        )

        projection_control_layout = self.make_projection_control_layout(
            styles=styles,
            parent=parent,
            projection_view=projection_view,
        )

        tabs = []
        if select_control_layout:
            tabs.append(
                bokeh.models.TabPanel(child=select_control_layout, title="Select")
            )
        tabs += [
            bokeh.models.TabPanel(child=images_control_layout, title="Supercell"),
            bokeh.models.TabPanel(child=markers_control_layout, title="Markers"),
            bokeh.models.TabPanel(child=colors_control_layout, title="Colors"),
            bokeh.models.TabPanel(
                child=projaxes_control_layout, title="Projection Axes"
            ),
            bokeh.models.TabPanel(
                child=projection_control_layout, title="Projection Type"
            ),
        ]

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
