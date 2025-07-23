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
from ._ViewAtomicStructure import (
    ViewAtomicStructure,
    make_prim_component_params,
)


class CabinetInput:
    def __init__(
        self,
        view_control,
        styles: DashboardStyles = None,
        parent: typing.Any = None,
        view_cabinet: ViewAtomicStructure = None,
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
        view_cabinet: ViewAtomicStructure
            The cabinet view.

        """
        self.view_control = view_control
        self.styles = styles
        self.parent = parent
        self.view_cabinet = view_cabinet

        # -- Make widgets ---

        # -- Output current view axes --
        self.view_basis_cart = None
        self.view_basis_frac = None
        self.view_basis_mb = None
        self.cabinet_scale_row = None
        self.cabinet_angle_row = None
        self.cabinet_rotation_angle_row = None

        self._update_view_basis()

        # Axes priority/order
        # self.cabinet_input_order_div = bokeh.models.Div(
        #     text="""<b>Axes to set</b>""", width=200
        # )
        self.cabinet_input_order_select = bokeh.models.Select(
            options=[key for key in self.view_control.cabinet_input_order_options],
            value=self.view_control.cabinet_input_order,
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
        # self.cabinet_input_mode_div = bokeh.models.Div(
        #     text="""<b>Input mode</b>""", width=200
        # )
        options = [
            ("frac", "Fractional"),
            ("cart", "Cartesian"),
            ("miller_bravais", "Miller-Bravais"),
        ]
        self.cabinet_input_mode_select = bokeh.models.Select(
            title="Mode",
            options=options,
            value=self.view_control.cabinet_input_mode,
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

        def update_cabinet_input_mode(attr, old, new):
            self.update_layout()

        self.cabinet_input_mode_select.on_change("value", update_cabinet_input_mode)

        def update_cabinet_input_order(attr, old, new):
            self.update_layout()

        self.cabinet_input_order_select.on_change("value", update_cabinet_input_order)

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
        view_basis = self.view_cabinet.view_basis

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

        # Cabinet scale display
        r = row(
            bokeh.models.Div(text="""<b>Cabinet scale: </b>""", width=140),
            bokeh.models.Div(
                text=f"""<b>{self.view_control.cabinet_scale:.3f}</b>""",
                width=80,
            ),
        )
        if self.cabinet_scale_row is None:
            self.cabinet_scale_row = r
        else:
            self.cabinet_scale_row.children = r.children

        # Cabinet angle display
        angle = self.view_control.cabinet_angle * 180 / math.pi
        r = row(
            bokeh.models.Div(text="""<b>Cabinet angle: </b>""", width=140),
            bokeh.models.Div(
                text=f"""<b>{(angle):.3f}</b>""",
                width=80,
            ),
        )
        if self.cabinet_angle_row is None:
            self.cabinet_angle_row = r
        else:
            self.cabinet_angle_row.children = r.children

        # Cabinet rotation angle display
        r = row(
            bokeh.models.Div(text="""<b>Rotation angle: </b>""", width=140),
            bokeh.models.Div(
                text=f"""<b>{self.view_control.cabinet_rotation_angle:.3f}</b>""",
                width=80,
            ),
        )
        if self.cabinet_rotation_angle_row is None:
            self.cabinet_rotation_angle_row = r
        else:
            self.cabinet_rotation_angle_row.children = r.children

    def make_layout(self):
        mode = self.cabinet_input_mode_select.value
        order = self.cabinet_input_order_select.value
        order_options = self.view_control.cabinet_input_order_options
        priority = order_options[order]

        mode_frac = "frac"
        mode_cart = "cart"
        mode_mb = "miller_bravais"

        # Display of current cabinet view basis
        self.view_basis_cart.visible = mode == mode_cart
        self.view_basis_frac.visible = mode == mode_frac
        self.view_basis_mb.visible = mode == mode_mb

        # Input of new cabinet view basis
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
                self.cabinet_input_mode_select,
                bokeh.models.Div(text="""<b>Current axes: </b>""", width=200),
                self.view_basis_frac,
                self.view_basis_cart,
                self.view_basis_mb,
                self.cabinet_scale_row,
                self.cabinet_angle_row,
                self.cabinet_rotation_angle_row,
                height=250,
                width=400,
            ),
            column(
                row(
                    self.cabinet_input_order_select,
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
        mode = self.cabinet_input_mode_select.value
        # order = self.cabinet_input_order_select.value
        # order_options = self.view_control.cabinet_input_order_options
        # priority = order_options[order]
        # self.layout.children = [
        #     self.cabinet_input_mode_select,
        #     self.cabinet_input_order_select,
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
        mode = self.cabinet_input_mode_select.value
        self.view_control.cabinet_input_mode = mode

        order = self.cabinet_input_order_select.value
        self.view_control.cabinet_input_order = order

        order_options = self.view_control.cabinet_input_order_options
        priority = order_options[order]

        # Highest priority input (match this direction exactly)
        x = [s.value for s in self.spinner[mode][priority[0] - 1]]
        self.view_control.cabinet_first_input = np.array(x)

        # Second highest priority input (make orthogonal to the first)
        x = [s.value for s in self.spinner[mode][priority[1] - 1]]
        self.view_control.cabinet_second_input = np.array(x)

        # -- Update the cabinet view axes --
        self.view_control.set_cabinet_view_axes()

        # -- Trigger view update --
        self.parent.trigger_update()


class ViewControl:
    def __init__(
        self,
        prim: casmconfig.Prim,
        component_params: typing.Optional[dict] = None,
    ):
        self.prim = prim

        self._input_component_params = copy.deepcopy(component_params)

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

        component_params = copy.deepcopy(self._input_component_params)
        if component_params is None:
            component_params = make_prim_component_params(prim=self.prim)
        self.component_params = component_params
        """dict[str, dict]: The bokeh scatter plot parameters used to draw atoms, with
        atom type name as key.

        Must include "color", "size", and "alpha". Additional bokeh plotting
        parameters like "line_color" and "line_width" may also be included. The
        same attributes must be present for all components.
        """

    def reset_cabinet_view(self):
        self.cabinet_scale = 0.2
        """float: The scale factor for the cabinet view"""

        self.cabinet_angle = math.pi / 6.0
        """float: The angle for the cabinet view"""

        self.cabinet_rotation_angle = 10.0
        """float: The angle to rotate, in degrees"""

        self.cabinet_v1 = np.array([1.0, 0.0, 0.0])
        """np.array[float]: The Cartesian vector for the horizontal axis of the 
        cabinet view."""

        self.cabinet_v2 = np.array([0.0, 0.0, 1.0])
        """np.array[float]: The Cartesian vector for the vertical axis of the 
        cabinet view."""

        self.cabinet_first_input = np.array([1.0, 0.0, 0.0])
        """np.array[float]: The Cartesian vector for the horizontal axis of the
        cabinet view."""

        self.cabinet_second_input = np.array([0.0, 0.0, 1.0])
        """np.array[float]: The Cartesian vector for the vertical axis of the
        cabinet view."""

        self.cabinet_input_mode = "cart"
        """str: Cabinet view axes input mode; one of "frac", "cart", or 
        "miller_bravais"."""

        self.cabinet_input_order_options = {
            "b1, b2": [1, 2, 3],
            "b1, b3": [1, 3, 2],
            "b3, b1": [3, 1, 2],
            "b3, b2": [3, 2, 1],
            "b2, b1": [2, 1, 3],
            "b2, b3": [2, 3, 1],
        }
        """dict: Options for the cabinet view axes input order."""

        self.cabinet_input_order = "b1, b2"
        """str: The current input order, as a key into `cabinet_input_order_options`."""

    def reset(self):
        self.reset_images()
        self.reset_markers()
        self.reset_cabinet_view()

        self._update_disabled = False
        """bool: Flag used internally to prevent triggering updates in some
        callbacks"""

    def _vector_to_cart(self, v):
        if v is None:
            return np.zeros((3,))
        L = self.prim.xtal_prim.lattice().column_vector_matrix()
        if self.cabinet_input_mode == "cart":
            return v
        elif self.cabinet_input_mode == "frac":
            return L @ v
        elif self.cabinet_input_mode == "miller_bravais":
            return L @ from_miller_bravais_direction(v)
        else:
            raise Exception("Cabinet view input mode error")

    def _vector_from_cart(self, v):
        size = 3
        if self.cabinet_input_mode == "miller_bravais":
            size = 4
        if v is None:
            return np.zeros((size,))
        if self.cabinet_input_mode == "cart":
            return v
        elif self.cabinet_input_mode == "frac":
            L = self.prim.xtal_prim.lattice().column_vector_matrix()
            return np.linalg.pinv(L) @ v
        elif self.cabinet_input_mode == "miller_bravais":
            L = self.prim.xtal_prim.lattice().column_vector_matrix()
            v_frac = np.linalg.pinv(L) @ v
            return to_miller_bravais_direction(v_frac)
        else:
            raise Exception("Cabinet view input mode error")

    def set_cabinet_view_axes(
        self,
    ):
        """Set the cabinet view axes"""

        priority = self.cabinet_input_order_options[self.cabinet_input_order]
        if len(priority) != 3 or list(set(priority)) != [1, 2, 3]:
            raise Exception("Cabinet view priority must be a permutation of [1, 2, 3]")

        input_axes = np.zeros((3, 3))
        input_axes[:, priority[0] - 1] = self._vector_to_cart(self.cabinet_first_input)
        input_axes[:, priority[1] - 1] = self._vector_to_cart(self.cabinet_second_input)
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
                        "Highest priority cabinet view axis cannot be length zero"
                    )
                first = x / norm
                new_axes[:, i_axis - 1] = first
            elif i_order == 1:
                x = input_axes[:, i_axis - 1]
                second = x - (x @ first) * first
                norm = np.linalg.norm(second)
                if np.isclose(norm, 0):
                    raise Exception(
                        "Second highest priority cabinet view axis cannot be parallel "
                        "to the highest priority view axis"
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
                    raise Exception("Cabinet view basis construction priority error")
                new_axes[:, i_axis - 1] = third
            else:
                raise Exception("Cabinet view basis construction error")

        self.cabinet_v1 = new_axes[:, 0]
        self.cabinet_v2 = new_axes[:, 1]

        self.cabinet_first_input = self._vector_from_cart(new_axes[:, priority[0] - 1])
        self.cabinet_second_input = self._vector_from_cart(new_axes[:, priority[1] - 1])

    def rotate_cabinet_view_basis(
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

        # Set the new cabinet_v1 and cabinet_v2
        self.cabinet_v1 = new_view_basis[:, 0]
        self.cabinet_v2 = new_view_basis[:, 1]

    def get_state(self):
        return {
            "a_range": self.images_a_range,
            "b_range": self.images_b_range,
            "c_range": self.images_c_range,
            "m_range": self.images_m_range,
            "marker_size_scale": self.marker_size_scale,
            "marker_alpha_scale": self.marker_alpha_scale,
            "cabinet_scale": self.cabinet_scale,
            "cabinet_angle": self.cabinet_angle,
            "cabinet_v1": self.cabinet_v1.tolist(),
            "cabinet_v2": self.cabinet_v2.tolist(),
        }

    def set_state(
        self,
        state: dict,
    ):
        self.images_a_range = state["a_range"]
        self.images_b_range = state["b_range"]
        self.images_c_range = state["c_range"]
        self.images_m_range = state["m_range"]
        self.marker_size_scale = state["marker_size_scale"]
        self.marker_alpha_scale = state["marker_alpha_scale"]
        self.cabinet_scale = state["cabinet_scale"]
        self.cabinet_angle = state["cabinet_angle"]
        self.cabinet_v1 = np.array(state["cabinet_v1"])
        self.cabinet_v2 = np.array(state["cabinet_v2"])

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

    def make_cabinet_view_control_layout(
        self,
        styles=None,
        parent=None,
        view_cabinet=None,
    ):
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

        # Cabinet rotation angle controls
        cabinet_rotation_angle_div = bokeh.models.Div(text="""<b>Rotation Angle:</b>""")
        cabinet_rotation_angle_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        cabinet_rotation_angle_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # Cabinet rotate controls
        cabinet_rotate_b1_div = bokeh.models.Div(text="""<b>Rotate b1:</b>""")
        cabinet_rotate_b1_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        cabinet_rotate_b1_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        cabinet_rotate_b2_div = bokeh.models.Div(text="""<b>Rotate b2:</b>""")
        cabinet_rotate_b2_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        cabinet_rotate_b2_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        cabinet_rotate_b3_div = bokeh.models.Div(text="""<b>Rotate b3:</b>""")
        cabinet_rotate_b3_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        cabinet_rotate_b3_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        # Cabinet view axes input
        cabinet_input = CabinetInput(
            view_control=self,
            styles=styles,
            parent=parent,
            view_cabinet=view_cabinet,
        )

        # Reset button:
        reset_button = bokeh.models.Button(label="Reset", button_type="success")

        # --- Callbacks ---

        def reset_button_action(attr):
            self.reset_cabinet_view()
            parent.trigger_update()
            cabinet_input._update_view_basis()

        reset_button.on_click(reset_button_action)

        # Cabinet scale controls
        def increase_cabinet_scale(attr):
            self.cabinet_scale *= 1.5
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_scale_inc.on_click(increase_cabinet_scale)

        def decrease_cabinet_scale(attr):
            self.cabinet_scale /= 1.5
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_scale_dec.on_click(decrease_cabinet_scale)

        # Cabinet angle controls
        def increase_cabinet_angle(attr):
            self.cabinet_angle += math.pi / 36.0
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_angle_inc.on_click(increase_cabinet_angle)

        def decrease_cabinet_angle(attr):
            self.cabinet_angle -= math.pi / 36.0
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_angle_dec.on_click(decrease_cabinet_angle)

        # Cabinet rotation angle controls
        def increase_cabinet_rotation_angle(attr):
            self.cabinet_rotation_angle += 1.0
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_rotation_angle_inc.on_click(increase_cabinet_rotation_angle)

        def decrease_cabinet_rotation_angle(attr):
            if self.cabinet_rotation_angle <= 1.0:
                return
            self.cabinet_rotation_angle -= 1.0
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_rotation_angle_dec.on_click(decrease_cabinet_rotation_angle)

        # Cabinet rotate controls
        def rotate_b1_inc(attr):
            self.rotate_cabinet_view_basis(
                np.array([1.0, 0.0, 0.0]),
                view_cabinet.view_basis,
                self.cabinet_rotation_angle,
            )
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_rotate_b1_inc.on_click(rotate_b1_inc)

        def rotate_b1_dec(attr):
            self.rotate_cabinet_view_basis(
                np.array([1.0, 0.0, 0.0]),
                view_cabinet.view_basis,
                -self.cabinet_rotation_angle,
            )
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_rotate_b1_dec.on_click(rotate_b1_dec)

        def rotate_b2_inc(attr):
            self.rotate_cabinet_view_basis(
                np.array([0.0, 1.0, 0.0]),
                view_cabinet.view_basis,
                self.cabinet_rotation_angle,
            )
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_rotate_b2_inc.on_click(rotate_b2_inc)

        def rotate_b2_dec(attr):
            self.rotate_cabinet_view_basis(
                np.array([0.0, 1.0, 0.0]),
                view_cabinet.view_basis,
                -self.cabinet_rotation_angle,
            )
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_rotate_b2_dec.on_click(rotate_b2_dec)

        def rotate_b3_inc(attr):
            self.rotate_cabinet_view_basis(
                np.array([0.0, 0.0, 1.0]),
                view_cabinet.view_basis,
                self.cabinet_rotation_angle,
            )
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_rotate_b3_inc.on_click(rotate_b3_inc)

        def rotate_b3_dec(attr):
            self.rotate_cabinet_view_basis(
                np.array([0.0, 0.0, 1.0]),
                view_cabinet.view_basis,
                -self.cabinet_rotation_angle,
            )
            parent.trigger_update()
            cabinet_input._update_view_basis()

        cabinet_rotate_b3_dec.on_click(rotate_b3_dec)

        # --- Layout ---

        c1b = cabinet_input.layout
        c2 = column(
            row(cabinet_scale_div, cabinet_scale_dec, cabinet_scale_inc),
            row(cabinet_angle_div, cabinet_angle_dec, cabinet_angle_inc),
            row(
                cabinet_rotation_angle_div,
                cabinet_rotation_angle_dec,
                cabinet_rotation_angle_inc,
            ),
            row(cabinet_rotate_b1_div, cabinet_rotate_b1_dec, cabinet_rotate_b1_inc),
            row(cabinet_rotate_b2_div, cabinet_rotate_b2_dec, cabinet_rotate_b2_inc),
            row(cabinet_rotate_b3_div, cabinet_rotate_b3_dec, cabinet_rotate_b3_inc),
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

    def make_controls_tabs_layout(
        self,
        select_control_layout: typing.Optional[typing.Any],
        styles: DashboardStyles,
        parent: typing.Any,
        view_cabinet: ViewAtomicStructure,
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
        view_cabinet: ViewAtomicStructure
            The cabinet view.

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

        cabinet_view_control_layout = self.make_cabinet_view_control_layout(
            styles=styles,
            parent=parent,
            view_cabinet=view_cabinet,
        )

        tabs = []
        if select_control_layout:
            tabs.append(
                bokeh.models.TabPanel(child=select_control_layout, title="Select")
            )
        tabs += [
            bokeh.models.TabPanel(child=images_control_layout, title="Supercell"),
            bokeh.models.TabPanel(child=markers_control_layout, title="Markers"),
            bokeh.models.TabPanel(
                child=cabinet_view_control_layout, title="Cabinet View"
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
        )

        # control_layout = column(
        #     images_control_layout,
        #     markers_control_layout,
        #     cabinet_view_control_layout,
        #     stylesheets=[
        #         styles.darkstyle,
        #         styles.typekit_stylesheet,
        #     ],
        # )

        return control_layout
