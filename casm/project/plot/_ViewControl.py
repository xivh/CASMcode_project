import copy
import math
import typing

import bokeh.models
import numpy as np
from bokeh.layouts import column, row

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal

from ._misc import (
    from_miller_bravais_direction,
    to_miller_bravais_direction,
)
from ._ViewAtomicStructure import (
    make_prim_component_params,
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
