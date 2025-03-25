import copy
import math
import os
import typing

import bokeh.models
import bokeh.palettes
import numpy as np
from bokeh.layouts import column, row

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal
from casm.twinfinder import (
    TwinfinderResult,
)

from ._ViewAtomicStructure import (
    ViewAtomicStructure,
    make_prim_component_params,
)


def from_miller_bravais_direction(uvtw_indices: np.ndarray):
    """Convert a (U,V,T,W) Miller-Bravais direction to a (u,v,w) Miller direction.

    Parameters
    ----------
    uvtw_indices: np.ndarray
        The Miller-Bravais direction, (U, V, T, W). May be 1d or 2d, as columns.

    Returns
    -------
    uvw_indices: np.ndarray
        The Miller direction in 3D, (u, v, w).
    """
    if len(uvtw_indices.shape) == 1:
        U, V, T, W = uvtw_indices
        u = U - T
        v = V - T
        w = W
        return np.array([u, v, w])
    else:
        result = np.zeros((3, uvtw_indices.shape[1]))
        for i in range(uvtw_indices.shape[1]):
            result[:, i] = from_miller_bravais_direction(uvtw_indices[:, i])
        return result


def to_miller_bravais_direction(uvw_indices: np.ndarray):
    """Convert a (u,v,w) Miller direction to a (U,V,T,W) Miller-Bravais direction.

    Parameters
    ----------
    uvw_indices: np.ndarray
        The Miller 3-index direction, (u, v, w). May be 1d or 2d, as columns.

    Returns
    -------
    uvtw_indices: np.ndarray
        The Miller-Bravais 4-index direction, (U,V,T,W).
    """
    if len(uvw_indices.shape) == 1:
        u, v, w = uvw_indices
        U = (2 * u - v) / 3
        V = (2 * v - u) / 3
        T = -(U + V)
        W = w
        return np.array([U, V, T, W])
    else:
        result = np.zeros((4, uvw_indices.shape[1]))
        for i in range(uvw_indices.shape[1]):
            result[:, i] = to_miller_bravais_direction(uvw_indices[:, i])
        return result


def almost_zero(value, abs_tol=1e-5) -> bool:
    """Check if value is approximately zero, using an absolute tolerance"""
    return abs(value) < abs_tol


def almost_equal(value1, value2, abs_tol=1e-5) -> bool:
    """Check if two values are approximately equal, using an absolute tolerance"""
    return almost_zero(value1 - value2, abs_tol=abs_tol)


def almost_int(value, abs_tol=1e-5) -> bool:
    """Check if a floating point value is approximately integer, using an \
    absolute tolerance"""
    return almost_zero(abs(value - round(value)), abs_tol=abs_tol)


def scale_to_int(v: np.ndarray, cutoff: int = 10) -> typing.Union[np.ndarray, str]:
    x = np.max([np.abs(np.max(v)), np.abs(np.min(v))])
    v = v / x

    any_fractions = True
    while any_fractions:
        any_fractions = False
        for i in range(len(v)):
            if not almost_int(v[i]):
                x = np.abs(v[i])
                v = v / (x - math.floor(x))
                any_fractions = True
        for i in range(len(v)):
            if np.abs(v[i]) > cutoff:
                return f"indices elements > {cutoff}"
    return v


def scale_columns_to_int_if_possible(M: np.ndarray, cutoff: int = 10) -> np.ndarray:
    """Scale the columns of a matrix to integers, if possible

    Parameters
    ----------
    M: np.ndarray
        The matrix to scale.
    cutoff: int
        The cutoff value for scaling.

    Returns
    -------
    scaled_M: np.ndarray
        The scaled matrix, or the original matrix if the cutoff was exceeded.
    """
    result = np.zeros(M.shape)
    for i in range(M.shape[1]):
        x = scale_to_int(M[:, i], cutoff=cutoff)
        if isinstance(x, str):
            return M
        result[:, i] = x
    return result


class DashboardStyles:
    def __init__(self):
        # -- Dark theme --
        self.darkstyle = bokeh.models.GlobalInlineStyleSheet(
            css="""
            * {
              font-family: roboto-mono;
            }

            @media (prefers-color-scheme: dark) {
              * {
                font-family: roboto-mono;
              }

              html {
                color-scheme: dark;
                color: #ddd;
              }
            }""",
        )

        self.dark_bk_input_style = bokeh.models.InlineStyleSheet(
            css="""
            @media (prefers-color-scheme: dark) {

            .bk-input {
              /* color: #bbb; */
              background-color:#222;
            }

            select:not([multiple]).bk-input, select:not([size]).bk-input {
              background-image: url('data:image/svg+xml;utf8,<svg version="1.1" viewBox="0 0 25 20" xmlns="http://www.w3.org/2000/svg"><path d="M 0,0 25,0 12.5,20 Z" fill="white" /></svg>');
            }

            .bk-input-group > .bk-spin-wrapper > .bk-spin-btn.bk-spin-btn-up:before {
              border-bottom: 5px solid white;
            }

            .bk-input-group > .bk-spin-wrapper > .bk-spin-btn.bk-spin-btn-down:before {
              border-top: 5px solid white;
            }

            .bk-btn-default {
              color: #ddd;
              background-color: #222;
              border-color: #ccc;
            }
            }
            """,  # noqa: E501
        )


class CabinetInput:
    def __init__(
        self,
        view_control,
        styles=None,
        parent=None,
    ):
        self.view_control = view_control
        self.styles = styles
        self.parent = parent

        # -- Make widgets ---

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
            title="Input mode",
            options=options,
            value=self.view_control.cabinet_input_mode,
            stylesheets=[self.styles.dark_bk_input_style],
        )

        # Update view button:
        self.update_button = bokeh.models.Button(
            label="Update view",
            button_type="success",
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

    def make_layout(self):
        mode = self.cabinet_input_mode_select.value
        order = self.cabinet_input_order_select.value
        order_options = self.view_control.cabinet_input_order_options
        priority = order_options[order]

        size = 3
        if mode == "miller_bravais":
            size = 4

        print("mode:", mode)
        print("priority:", priority)
        print(
            "spinners (first):", [type(x) for x in self.spinner[mode][priority[0] - 1]]
        )
        print(
            "spinners (second):", [type(x) for x in self.spinner[mode][priority[1] - 1]]
        )

        self.layout = column(
            self.cabinet_input_mode_select,
            self.cabinet_input_order_select,
            self.update_button,
            row(*[x for x in self.spinner[mode][priority[0] - 1]]),
            row(*[x for x in self.spinner[mode][priority[1] - 1]]),
            width=size * 100,
            margin=(0, 10),
        )

    def update_layout(self):
        mode = self.cabinet_input_mode_select.value
        order = self.cabinet_input_order_select.value
        order_options = self.view_control.cabinet_input_order_options
        priority = order_options[order]

        self.layout.children = [
            self.cabinet_input_mode_select,
            self.cabinet_input_order_select,
            self.update_button,
            row(*[x for x in self.spinner[mode][priority[0] - 1]]),
            row(*[x for x in self.spinner[mode][priority[1] - 1]]),
        ]

    def update_view(self):
        # -- Get the view input --

        # - Input mode -
        mode = self.cabinet_input_mode_select.value
        self.view_control.cabinet_input_mode = mode

        order = self.cabinet_input_order_select.value
        self.view_control.cabinet_input_order = order

        order_options = self.view_control.cabinet_input_order_options
        priority = order_options[order]

        print("mode:", mode)
        print("order:", order)
        print("priority:", priority)

        # Highest priority input (match this direction exactly)
        x = [s.value for s in self.spinner[mode][priority[0] - 1]]
        self.view_control.cabinet_first_input = np.array(x)
        print("cabinet_first_input:", self.view_control.cabinet_first_input)

        # Second highest priority input (make orthogonal to the first)
        x = [s.value for s in self.spinner[mode][priority[1] - 1]]
        self.view_control.cabinet_second_input = np.array(x)
        print("cabinet_second_input:", self.view_control.cabinet_second_input)

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

        print("set_cabinet_view_axes")
        priority = self.cabinet_input_order_options[self.cabinet_input_order]
        if len(priority) != 3 or list(set(priority)) != [1, 2, 3]:
            raise Exception("Cabinet view priority must be a permutation of [1, 2, 3]")

        input_axes = np.zeros((3, 3))
        input_axes[:, priority[0] - 1] = self._vector_to_cart(self.cabinet_first_input)
        input_axes[:, priority[1] - 1] = self._vector_to_cart(self.cabinet_second_input)
        input_axes[:, priority[2] - 1] = self._vector_to_cart(None)

        print("input_axes:")
        print(input_axes)

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
                print("first:", first)
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
                print("second:", second)
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
                print("third:", third)
            else:
                raise Exception("Cabinet view basis construction error")

        print("new_axes:\n", new_axes)
        self.cabinet_v1 = new_axes[:, 0]
        self.cabinet_v2 = new_axes[:, 1]
        print("v1:", self.cabinet_v1)
        print("v2:", self.cabinet_v2)

        self.cabinet_first_input = self._vector_from_cart(new_axes[:, priority[0] - 1])
        self.cabinet_second_input = self._vector_from_cart(new_axes[:, priority[1] - 1])
        print("cabinet_first_input:", self.cabinet_first_input)
        print("cabinet_second_input:", self.cabinet_second_input)
        print()

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
        images_div = bokeh.models.Div(text="""<b># Images</b>""", width=200)
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
        return row(c1, c2)

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
        )
        c2 = column(
            reset_button,
            width=200,
            margin=(0, 10),
        )
        return row(c1, c2)

    def make_cabinet_view_control_layout(
        self,
        styles=None,
        parent=None,
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

        # Cabinet view axes input
        cabinet_input = CabinetInput(
            view_control=self,
            styles=styles,
            parent=parent,
        )

        # Reset button:
        reset_button = bokeh.models.Button(label="Reset", button_type="success")

        # --- Callbacks ---

        def reset_button_action(attr):
            self.reset_cabinet_view()
            parent.trigger_update()

        reset_button.on_click(reset_button_action)

        # Cabinet scale controls
        def increase_cabinet_scale(attr):
            self.cabinet_scale *= 1.5
            parent.trigger_update()

        cabinet_scale_inc.on_click(increase_cabinet_scale)

        def decrease_cabinet_scale(attr):
            self.cabinet_scale /= 1.5
            parent.trigger_update()

        cabinet_scale_dec.on_click(decrease_cabinet_scale)

        # Cabinet angle controls
        def increase_cabinet_angle(attr):
            self.cabinet_angle += math.pi / 36.0
            parent.trigger_update()

        cabinet_angle_inc.on_click(increase_cabinet_angle)

        def decrease_cabinet_angle(attr):
            self.cabinet_angle -= math.pi / 36.0
            parent.trigger_update()

        cabinet_angle_dec.on_click(decrease_cabinet_angle)

        # --- Layout ---

        c1b = cabinet_input.layout
        c2 = column(
            row(cabinet_scale_div, cabinet_scale_dec, cabinet_scale_inc),
            row(cabinet_angle_div, cabinet_angle_dec, cabinet_angle_inc),
            width=200,
            margin=(0, 10),
        )
        c3 = column(
            reset_button,
            width=200,
            margin=(0, 10),
        )
        layout = row(c1b, c2, c3)

        return layout


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
        # if self.size() == 0:
        #     return

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

        # invariant_plane_text.text = make_invariant_plane_text(
        #     self.invariant_plane_str
        # )
        # shear_direction_text.text = make_shear_direction_text(
        #     self.shear_direction_str
        # )
        # shear_text.text = make_shear_text(self.shear_str)
        # image_symmetry_text.text = make_image_symmetry_text("g")
        # cost_text.text = make_cost_text(self.cost_str)

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


class TwinfinderResultsDashboard:
    """Dashboard for viewing ScoredStructureMapping from a
    list[ScoredStructureMapping]"""

    def __init__(
        self,
        prim: casmconfig.Prim,
        results: list[TwinfinderResult],
        component_params: typing.Optional[dict] = None,
        page_size: int = 100,
    ):
        """

        Parameters
        ----------
        prim: libcasm.configuration.Prim
            The primitive cell.
        results: list[TwinfinderResult],
            The results to visualize.
        component_params: dict[str, dict]
            The bokeh scatter plot parameters used to draw atoms, with
            atom type name as key.

            Must include "color", "size", and "alpha". Additional bokeh plotting
            parameters like "line_color" and "line_width" may also be included. The
            same attributes must be present for all components.
        page_size: int = 100
            The number of results to show per "page".
        """
        self.prim = prim
        """libcasm.configuration.Prim: The primitive cell."""

        self.results = results
        """list[casm.twinfinder.TwinfinderResult]: The results to visualize."""

        self.view_control = ViewControl(
            prim=self.prim,
            component_params=component_params,
        )

        self.page_size = page_size

        self.selected_structure = None
        """libcasm.xtal.Structure: The structure to visualize."""

        self.n_images = 11
        """int: The number of images along the chain from parent to child (including 
        the parent and child)."""

        self.selected_chain_orbit = None
        """list[list[libcasm.xtal.Structure]]: The orbit of chains of structures to 
        visualize."""

        self.selected_chain_info = None
        """list[dict]: Invariant information about structures along the chain."""

        self.selected_image_index = None
        """int: The index of the selected image in the chain from parent (0) to child 
        (n_images-1)."""

        self.selected_chain_index = None
        """int: Which chain in the orbit to visualize."""

        self.selected_result_index = None
        """int: The index of the selected result in the list."""

        self.selected_page_number = None
        """int: The page"""

        self.run_on = False
        """bool: Whether running back-and-forth along the chain is on or off"""

        self.run_direction = 1
        """int: Use -1,1 to indicate decreasing, increasing"""

        self.options = ["(None)"]
        """list[str]: The result index options for the current page"""

        self.chain_index_options = ["(None)"]
        """list[str]: The chain index options for the current result"""

        self.image_index_options = ["(None)"]
        """list[str]: The image index options for the current result"""

        self.selected_result = None
        """casm.twinfinder.TwinfinderRestul: The selected result"""

        self.selected_name = None
        """str: The name of the selected result / chain / image"""

        self._run_button_callback_id = None
        """int: The callback id for the run button"""

        self._update_disabled = False
        """bool: Flag used internally to prevent triggering updates in some
        callbacks"""

        self.view_control.reset()

        # -- Set the initial selection --
        if self.size() != 0:
            self.set_result_index(0)

    def size(self):
        """Return the size of the dashboard"""
        return len(self.results)

    def set_result_index(
        self,
        result_index: int,
    ):
        if self.size() == 0:
            return
        if result_index < 0 or result_index >= self.size():
            raise ValueError(
                f"Error setting result index: " f"'{result_index}' not valid"
            )

        # determine page number from result index
        page_number = int(result_index / self.page_size) + 1

        # determine result index options on the page,
        # and prefix/postfix with (prev)/(next) if needed
        begin = (page_number - 1) * self.page_size
        end = page_number * self.page_size - 1
        if end >= self.size():
            end = self.size() - 1
        options = []
        if begin != 0:
            options.append("(prev)")
        options += [str(i) for i in range(begin, end + 1)]
        if end < self.size() - 1:
            options.append("(next)")

        if self.selected_image_index is None:
            self.selected_image_index = 0

        self.selected_page_number = page_number
        self.options = options
        self.selected_result_index = result_index
        self.selected_result = self.results[result_index]

        f_chain = np.linspace(0, 1, self.n_images)
        chain_orbit, chain_info = self.selected_result.make_chain_orbit(
            f_chain=f_chain,
        )
        # for i_chain, chain in enumerate(chain_orbit):
        #     for i_image, image in enumerate(chain):
        #         vol = image.lattice().volume()

        self.selected_chain_orbit = chain_orbit
        self.selected_chain_info = chain_info
        self.chain_index_options = [
            str(i) for i in range(len(self.selected_chain_orbit))
        ]
        self.image_index_options = [str(i) for i in range(self.n_images)]

        self.invariant_plane_str = self.selected_result.invariant_plane_str()
        self.shear_direction_str = self.selected_result.shear_direction_str()
        self.shear_str = self.selected_result.shear_str()
        self.cost_str = self.selected_result.cost_str()

        self.set_chain_index(chain_index=0)

    def set_chain_index(self, chain_index: int):
        if self.size() == 0:
            return

        self.selected_chain_index = chain_index
        self.set_image_index(image_index=self.selected_image_index)

    def set_image_index(self, image_index: int):
        if self.size() == 0:
            return

        self.selected_image_index = image_index

        # Update selected structure
        chain = self.selected_chain_orbit[self.selected_chain_index]
        self.selected_structure = self.view_control.make_superstructure(
            init_structure=chain[self.selected_image_index],
        )
        # Update name
        result_index = self.selected_result_index
        chain_index = self.selected_chain_index
        f = self.selected_image_index / (self.n_images - 1)
        name = f"Index={result_index}, Equiv={chain_index}, f={f}"
        self.selected_name = name

    def make_layout(
        self,
        doc=None,
        state=None,
    ):
        # --bokeh-icon-color: #fff;
        styles = DashboardStyles()

        # Page number selection:
        page_number_div = bokeh.models.Div(text="""<b>Page number</b>""", width=200)
        page_number_options = ["(None)"]
        page_number_value = "(None)"
        if self.selected_page_number is not None:

            def make_label(i):
                # page 1: (0-99)
                # page 2: (100-199)
                # etc.
                begin = (i - 1) * self.page_size
                end = i * self.page_size - 1
                if end >= self.size():
                    end = self.size() - 1
                return f"Pg. {i}: ({begin}-{end})"

            max_page_number = int((self.size() - 1) / self.page_size) + 1
            page_number_options = [
                (i, make_label(i)) for i in range(1, max_page_number + 1)
            ]
            page_number_value = self.selected_page_number
        page_number_select = bokeh.models.Select(
            # title="Page number",
            options=page_number_options,
            value=page_number_value,
            stylesheets=[styles.dark_bk_input_style],
        )

        # Result index selection:
        result_index_div = bokeh.models.Div(text="""<b>Result index</b>""", width=200)
        value = "(None)"
        if self.selected_page_number is not None:
            value = str(self.selected_result_index)
        result_index_select = bokeh.models.Select(
            # title="Result index",
            options=self.options,
            value=value,
            stylesheets=[styles.dark_bk_input_style],
        )

        # Chain index selection:
        chain_index_div = bokeh.models.Div(
            text="""<b>Equivalent mapping index</b>""", width=200
        )
        value = "(None)"
        if self.selected_page_number is not None:
            value = str(self.selected_chain_index)
        chain_index_select = bokeh.models.Select(
            # title="Equivalent mapping index",
            options=self.chain_index_options,
            value=value,
            stylesheets=[styles.dark_bk_input_style],
        )

        # Image index selection:
        image_index_div = bokeh.models.Div(
            text="""<b>Interpolation index</b>""", width=200
        )
        value = "(None)"
        if self.selected_page_number is not None:
            value = str(self.selected_image_index)
        image_index_select = bokeh.models.Select(
            # title="Equivalent mapping index",
            options=self.image_index_options,
            value=value,
            stylesheets=[styles.dark_bk_input_style],
        )

        # Text output:
        def make_invariant_plane_text(plane):
            return f"""<b>Plane:</b> {plane}"""

        def make_shear_direction_text(direction):
            return f"""<b>Direction:</b> {direction}"""

        def make_shear_text(shear):
            return f"""<b>Shear:</b> {shear}"""

        # def make_image_symmetry_text(symmetry):
        #     return f"""<b>Space group:</b> {symmetry}"""

        def make_cost_text(cost):
            return f"""<b>Tot/Lat/Atm Cost:</b> {cost}"""

        text_width = 400
        invariant_plane_text = bokeh.models.Div(
            text=make_invariant_plane_text(self.invariant_plane_str), width=text_width
        )
        shear_direction_text = bokeh.models.Div(
            text=make_shear_direction_text(self.shear_direction_str), width=text_width
        )
        shear_text = bokeh.models.Div(
            text=make_shear_text(self.shear_str), width=text_width
        )
        # image_symmetry_text = bokeh.models.Div(
        #     text=make_image_symmetry_text("g"), width=text_width
        # )
        cost_text = bokeh.models.Div(
            text=make_cost_text(self.cost_str), width=text_width
        )

        # Open with button:
        open_with_button = bokeh.models.Button(
            label="Open with VESTA", button_type="success"
        )

        # Run button:
        run_button = bokeh.models.Button(label="► Play", button_type="success")

        # Make view:
        self.projection_view = ProjectionView(view_control=self.view_control)

        def _trigger_update():
            if self.selected_structure is None:
                return

            self.set_image_index(self.selected_image_index)
            self.projection_view.set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )
            self.projection_view.view_cabinet.plot.title.text = self.selected_name

            invariant_plane_text.text = make_invariant_plane_text(
                self.invariant_plane_str
            )
            shear_direction_text.text = make_shear_direction_text(
                self.shear_direction_str
            )
            shear_text.text = make_shear_text(self.shear_str)
            # image_symmetry_text.text = make_image_symmetry_text("g")
            cost_text.text = make_cost_text(self.cost_str)

        self.trigger_update = _trigger_update

        if self.selected_structure is not None:
            self.projection_view.set_structure(
                structure=self.selected_structure,
                name=self.selected_name,
            )

        def do_result_index_update(
            result_index: int,
        ):
            if self.size() == 0:
                return

            self.set_result_index(result_index=result_index)

            # --- Update the widgets without triggers ---
            self._update_disabled = True
            page_number_select.value = self.selected_page_number
            result_index_select.value = str(self.selected_result_index)
            result_index_select.options = self.options
            chain_index_select.value = str(self.selected_chain_index)
            chain_index_select.options = self.chain_index_options
            image_index_select.value = str(self.selected_image_index)
            image_index_select.options = self.image_index_options
            self._update_disabled = False
            # --------------------------------------------

            self.trigger_update()

        def page_number_update(attr, old, new):
            if self._update_disabled:
                return
            result_index = (new - 1) * self.page_size
            do_result_index_update(result_index=result_index)

        page_number_select.on_change("value", page_number_update)

        def result_index_update(attr, old, new):
            if self._update_disabled:
                return

            if new == "(next)":
                new_page = self.selected_page_number + 1
                new_result_index = (new_page - 1) * self.page_size
                do_result_index_update(
                    result_index=new_result_index,
                )
            elif new == "(prev)":
                new_page = self.selected_page_number - 1
                new_result_index = new_page * self.page_size - 1
                do_result_index_update(
                    result_index=new_result_index,
                )
            else:
                do_result_index_update(result_index=int(new))

        result_index_select.on_change("value", result_index_update)

        def chain_index_update(attr, old, new):
            if self._update_disabled:
                return

            self.set_chain_index(chain_index=int(new))

            # --- Update the widgets without triggers ---
            self._update_disabled = True
            chain_index_select.value = str(self.selected_chain_index)
            self._update_disabled = False
            # --------------------------------------------

            self.trigger_update()

        chain_index_select.on_change("value", chain_index_update)

        def image_index_update(attr, old, new):
            if self._update_disabled:
                return

            self.set_image_index(image_index=int(new))

            # --- Update the widgets without triggers ---
            self._update_disabled = True
            image_index_select.value = str(self.selected_image_index)
            self._update_disabled = False
            # --------------------------------------------

            self.trigger_update()

        image_index_select.on_change("value", image_index_update)

        def open_with_vesta(attr):
            # make a temporary directory:
            import subprocess

            if self.size() == 0:
                return

            r = self.selected_result_index
            c = self.selected_chain_index
            i = self.selected_image_index
            name = f"twin-{r}-{c}-{i}.vasp"
            with open(name, "w") as f:
                f.write(self.selected_structure.to_poscar_str())
                f.flush()
                os.fsync(f.fileno())

            subprocess.run(
                [
                    "open",
                    "-a",
                    "/Applications/VESTA/VESTA.app",
                    name,
                ]
            )

        open_with_button.on_click(open_with_vesta)

        # Run button action

        def animate_update():
            if self.run_on:
                next_image_index = self.selected_image_index + self.run_direction
                if next_image_index < 0:
                    self.run_direction = 1
                    next_image_index = 0
                if next_image_index >= self.n_images:
                    self.run_direction = -1
                    next_image_index = self.n_images - 1

                self.set_image_index(image_index=next_image_index)
                # --- Update the widgets without triggers ---
                self._update_disabled = True
                image_index_select.value = str(self.selected_image_index)
                self._update_disabled = False
                # --------------------------------------------

                self.trigger_update()

        def animate():
            if self.run_on is False:
                self.run_on = True
                run_button.label = "❚❚ Pause"
                if doc is not None:
                    self._run_button_callback_id = doc.add_periodic_callback(
                        animate_update, 200
                    )
            else:
                self.run_on = False
                run_button.label = "► Play"
                if doc is not None:
                    doc.remove_periodic_callback(self._run_button_callback_id)

        run_button.on_click(animate)

        # Controls layout
        c1 = column(
            page_number_div,
            page_number_select,
            result_index_div,
            result_index_select,
            chain_index_div,
            chain_index_select,
            image_index_div,
            image_index_select,
            width=200,
            margin=(0, 10),
        )

        c2 = column(
            invariant_plane_text,
            shear_direction_text,
            shear_text,
            # image_symmetry_text,
            cost_text,
            width=400,
            margin=(0, 10),
        )

        c3 = column(
            open_with_button,
            run_button,
            width=200,
            margin=(0, 10),
        )

        # controls_row = row(c1, column(row(view_control_layout, c4), row(c5)))
        results_control_layout = row(c1, c2, c3)

        images_control_layout = self.view_control.make_images_control_layout(
            styles=styles,
            parent=self,
        )

        markers_control_layout = self.view_control.make_markers_control_layout(
            styles=styles,
            parent=self,
        )

        cabinet_view_control_layout = (
            self.view_control.make_cabinet_view_control_layout(
                styles=styles,
                parent=self,
            )
        )

        control_layout = bokeh.models.Tabs(
            tabs=[
                bokeh.models.TabPanel(child=results_control_layout, title="Results"),
                bokeh.models.TabPanel(child=images_control_layout, title="Images"),
                bokeh.models.TabPanel(child=markers_control_layout, title="Markers"),
                bokeh.models.TabPanel(
                    child=cabinet_view_control_layout, title="Cabinet View"
                ),
            ]
        )

        # Figures grid
        projection_view_layout = self.projection_view.make_layout()

        # Overall layout
        layout = column(
            # controls_row,
            control_layout,
            projection_view_layout,
            stylesheets=[styles.darkstyle],
        )

        return layout
