import copy
import math
import os
import typing

import bokeh.models
import bokeh.palettes
import numpy as np

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal

from ._ViewAtomicStructure import (
    ViewAtomicStructure,
    make_prim_component_params,
)


class ConfigurationListDashboard:
    """Dashboard for viewing Configurations from a list[Configuration]"""

    def __init__(
        self,
        configuration_list: list[casmconfig.Configuration],
        component_params: typing.Optional[dict] = None,
        page_size: int = 100,
    ):
        """

        Parameters
        ----------
        configuration_list: list[libcasm.configuration]
            The configuration list to visualize.
        component_params: dict[str, dict]
            The bokeh scatter plot parameters used to draw atoms, with
            atom type name as key.

            Must include "color", "size", and "alpha". Additional bokeh plotting
            parameters like "line_color" and "line_width" may also be included. The
            same attributes must be present for all components.
        page_size: int = 100
            The number of configurations to show per "page".
        """

        self.configuration_list = configuration_list
        """casm.configuration.ConfigurationSet: The configuration set"""

        self._input_component_params = copy.deepcopy(component_params)

        self.page_size = page_size

        self.selected_structure = None
        """libcasm.xtal.Structure: The structure of the selected configuration"""

        self.selected_configuration_index = None
        """int: The index of the selected configuration in the list - as a string."""

        self.selected_page_number = None
        """str: The page"""

        self.options = ["(None)"]
        """list[str]: The configuration index options for the current page"""

        self.selected_configuration = None
        """libcasm.configuration.Configuration: The selected configuration"""

        self.selected_configuration_name = None
        """str: The name of the selected configuration"""

        self.reset_view()

        # -- Set the initial supercell and configuration --
        if len(self.configuration_list) != 0:
            self.set_configuration_index(0)

    def reset_view(self):
        self.images_a_range = 1
        """int: The number of periodic images to show along the a-axis"""

        self.images_b_range = 1
        """int: The number of periodic images to show along the a-axis"""

        self.images_c_range = 1
        """int: The number of periodic images to show along the a-axis"""

        self.images_m_range = 1
        """int: The number of periodic images to show along the a-, b-, and c-axis"""

        self.marker_size_scale = 1.0
        """float: The scale factor for the marker size"""

        self.marker_alpha_scale = 1.0
        """float: The alpha value for the marker alpha"""

        self.cabinet_scale = 0.2
        """float: The scale factor for the cabinet view"""

        self.cabinet_angle = math.pi / 6.0
        """float: The angle for the cabinet view"""

        component_params = copy.deepcopy(self._input_component_params)
        if component_params is None and len(self.configuration_list) != 0:
            # Get first record in configuration set:
            configuration = next(iter(self.configuration_list))
            component_params = make_prim_component_params(
                prim=configuration.supercell.prim
            )
        self.component_params = component_params
        """dict[str, dict]: The bokeh scatter plot parameters used to draw atoms, with
        atom type name as key.

        Must include "color", "size", and "alpha". Additional bokeh plotting
        parameters like "line_color" and "line_width" may also be included. The
        same attributes must be present for all components.
        """

        self._update_disabled = False
        """bool: Flag used internally to prevent triggering updates in some
        callbacks"""

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

    def set_configuration_index(
        self,
        configuration_index: int,
    ):
        if len(self.configuration_list) == 0:
            return
        if configuration_index < 0 or configuration_index >= len(
            self.configuration_list
        ):
            raise ValueError(
                f"Error setting configuration index: "
                f"'{configuration_index}' not valid"
            )

        # determine page number from configuration index
        page_number = int(configuration_index / self.page_size) + 1

        # determine configuration index options on the page,
        # and prefix/postfix with (prev)/(next) if needed
        begin = (page_number - 1) * self.page_size
        end = page_number * self.page_size - 1
        if end >= len(self.configuration_list):
            end = len(self.configuration_list) - 1
        options = []
        if begin != 0:
            options.append("(prev)")
        options += [str(i) for i in range(begin, end + 1)]
        if end < len(self.configuration_list) - 1:
            options.append("(next)")

        # Get configuration name
        supercell = self.configuration_list[configuration_index].supercell
        supercell_name = casmconfig.SupercellRecord(supercell).supercell_name
        configuration_name = f"Index={configuration_index}, Supercell={supercell_name}"

        self.selected_page_number = page_number
        self.options = options
        self.selected_configuration_index = configuration_index
        self.selected_configuration = self.configuration_list[configuration_index]
        self.selected_configuration_name = configuration_name

        a = self.images_a_range
        b = self.images_b_range
        c = self.images_c_range
        m = self.images_m_range
        structure = xtal.make_structure_within(
            init_structure=self.selected_configuration.to_structure(
                excluded_species=[],
            )
        )
        superstructure = xtal.make_superstructure(
            transformation_matrix_to_super=np.diag([a, b, c]) * m,
            structure=structure,
        )

        self.selected_structure = superstructure

    def make_layout(self):
        # --bokeh-icon-color: #fff;
        darkstyle = copy.deepcopy(self.darkstyle)
        dark_bk_input_style = copy.deepcopy(self.dark_bk_input_style)

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
                return f"Pg. {i}: ({begin}-{end})"

            n_configs = len(self.configuration_list)
            max_page_number = int((n_configs - 1) / self.page_size) + 1
            page_number_options = [
                (i, make_label(i)) for i in range(1, max_page_number + 1)
            ]
            page_number_value = self.selected_page_number
        page_number_select = bokeh.models.Select(
            # title="Page number",
            options=page_number_options,
            value=page_number_value,
            stylesheets=[dark_bk_input_style],
        )

        # Configuration index selection:
        configuration_index_div = bokeh.models.Div(
            text="""<b>Configuration index</b>""", width=200
        )
        value = "(None)"
        if self.selected_page_number is not None:
            value = str(self.selected_configuration_index)
        configuration_index_select = bokeh.models.Select(
            # title="Configuration index",
            options=self.options,
            value=value,
            stylesheets=[dark_bk_input_style],
        )

        # Open with button:
        open_with_button = bokeh.models.Button(
            label="Open with VESTA", button_type="success"
        )

        # Reset button:
        reset_button = bokeh.models.Button(label="Reset", button_type="success")

        # Marker scale controls
        marker_size_scale_div = bokeh.models.Div(
            text="""<b>Marker Size:&nbsp;&nbsp;</b>"""
        )
        marker_size_scale_inc = bokeh.models.Button(
            label="+", stylesheets=[dark_bk_input_style]
        )
        marker_size_scale_dec = bokeh.models.Button(
            label="-", stylesheets=[dark_bk_input_style]
        )

        # Marker alpha controls
        marker_alpha_scale_div = bokeh.models.Div(text="""<b>Marker Alpha:&nbsp;</b>""")
        marker_alpha_scale_inc = bokeh.models.Button(
            label="+", stylesheets=[dark_bk_input_style]
        )
        marker_alpha_scale_dec = bokeh.models.Button(
            label="-", stylesheets=[dark_bk_input_style]
        )

        # Cabinet scale controls
        cabinet_scale_div = bokeh.models.Div(text="""<b>Cabinet Scale:</b>""")
        cabinet_scale_inc = bokeh.models.Button(
            label="+", stylesheets=[dark_bk_input_style]
        )
        cabinet_scale_dec = bokeh.models.Button(
            label="-", stylesheets=[dark_bk_input_style]
        )

        # Cabinet angle controls
        cabinet_angle_div = bokeh.models.Div(text="""<b>Cabinet Angle:</b>""")
        cabinet_angle_inc = bokeh.models.Button(
            label="+", stylesheets=[dark_bk_input_style]
        )
        cabinet_angle_dec = bokeh.models.Button(
            label="-", stylesheets=[dark_bk_input_style]
        )

        # Periodic range controls
        images_div = bokeh.models.Div(text="""<b># Periodic images</b>""", width=200)
        params = dict(width=80, low=1, high=None, step=1)
        images_a_range = bokeh.models.Spinner(
            title="Along `a`",
            value=self.images_a_range,
            stylesheets=[dark_bk_input_style],
            **params,
        )
        images_b_range = bokeh.models.Spinner(
            title="Along `b`",
            value=self.images_b_range,
            stylesheets=[dark_bk_input_style],
            **params,
        )
        images_c_range = bokeh.models.Spinner(
            title="Along `c`",
            value=self.images_c_range,
            stylesheets=[dark_bk_input_style],
            **params,
        )
        images_m_range = bokeh.models.Spinner(
            title="Mult.",
            value=self.images_c_range,
            low=1,
            high=None,
            step=1,
            stylesheets=[dark_bk_input_style],
        )

        view_xz = ViewAtomicStructure(
            doc=None,
            component_params=self.component_params,
            v1=[1.0, 0.0, 0.0],
            v2=[0.0, 0.0, 1.0],
        )

        view_yz = ViewAtomicStructure(
            doc=None,
            component_params=self.component_params,
            v1=[0.0, 1.0, 0.0],
            v2=[0.0, 0.0, 1.0],
        )

        view_xy = ViewAtomicStructure(
            doc=None,
            component_params=self.component_params,
            v1=[1.0, 0.0, 0.0],
            v2=[0.0, 1.0, 0.0],
        )

        view_cabinet = ViewAtomicStructure(
            doc=None,
            component_params=self.component_params,
            cabinet=(0.2, math.pi / 6.0),
        )

        # Set / update the configuration being viewed
        # - This updates bokeh data sources for each of the plots based on
        #   the current structure and parameters, so it is also used for
        #   updates to view ranges, cabinet, etc. parameters
        def set_configuration(
            structure: xtal.Structure,
            configuration_name: str,
        ):
            if len(self.configuration_list) == 0:
                return

            view_xz.set_structure(
                structure=structure,
                title="X-Z plane view",
                new_marker_size_scale=self.marker_size_scale,
                new_marker_alpha_scale=self.marker_alpha_scale,
            )
            view_yz.set_structure(
                structure=structure,
                title="Y-Z plane view",
                new_marker_size_scale=self.marker_size_scale,
                new_marker_alpha_scale=self.marker_alpha_scale,
            )
            view_xy.set_structure(
                structure=structure,
                title="X-Y plane view",
                new_marker_size_scale=self.marker_size_scale,
                new_marker_alpha_scale=self.marker_alpha_scale,
            )
            view_cabinet.set_structure(
                structure=structure,
                title=configuration_name,
                new_marker_size_scale=self.marker_size_scale,
                new_marker_alpha_scale=self.marker_alpha_scale,
                new_cabinet=(self.cabinet_scale, self.cabinet_angle),
            )

        if self.selected_structure is not None:
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )
        p_cabinet = view_cabinet.make_plot()

        def do_configuration_index_update(
            configuration_index: int,
        ):
            if len(self.configuration_list) == 0:
                return

            self.set_configuration_index(configuration_index=configuration_index)

            # --- Update the widgets without triggers ---
            self._update_disabled = True
            page_number_select.value = self.selected_page_number
            configuration_index_select.value = str(self.selected_configuration_index)
            configuration_index_select.options = self.options
            self._update_disabled = False
            # --------------------------------------------

            set_configuration(
                structure=self.selected_structure.copy(),
                configuration_name=self.selected_configuration_name,
            )
            p_cabinet.title.text = view_cabinet.title

        def page_number_update(attr, old, new):
            if self._update_disabled:
                return
            configuration_index = (new - 1) * self.page_size
            do_configuration_index_update(configuration_index=configuration_index)

        page_number_select.on_change("value", page_number_update)

        def configuration_index_update(attr, old, new):
            if self._update_disabled:
                return

            if new == "(next)":
                # do_supercell_name_update(next_supercell)
                new_page = self.selected_page_number + 1
                new_configuration_index = (new_page - 1) * self.page_size
                do_configuration_index_update(
                    configuration_index=new_configuration_index,
                )
            elif new == "(prev)":
                new_page = self.selected_page_number - 1
                new_configuration_index = new_page * self.page_size - 1
                do_configuration_index_update(
                    configuration_index=new_configuration_index,
                )
            else:
                do_configuration_index_update(configuration_index=int(new))

        configuration_index_select.on_change("value", configuration_index_update)

        def open_with_vesta(attr):
            # make a temporary directory:
            import subprocess

            if len(self.configuration_list) == 0:
                return

            name = self.selected_configuration_name.replace("/", ".") + ".vasp"
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

        def reset_button_action(attr):
            self.reset_view()

            # --- Update the widgets without triggers ---
            self._update_disabled = True
            images_a_range.value = self.images_a_range
            images_b_range.value = self.images_b_range
            images_c_range.value = self.images_c_range
            images_m_range.value = self.images_m_range
            self._update_disabled = False
            # --------------------------------------------

            self.set_configuration_index(self.selected_configuration_index)
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        reset_button.on_click(reset_button_action)

        # Periodic range - callbacks
        def update_a_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_a_range = new
            self.set_configuration_index(self.selected_configuration_index)
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        def update_b_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_b_range = new
            self.set_configuration_index(self.selected_configuration_index)
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        def update_c_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_c_range = new
            self.set_configuration_index(self.selected_configuration_index)
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        def update_m_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_m_range = new
            self.set_configuration_index(self.selected_configuration_index)
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        images_a_range.on_change("value", update_a_range)
        images_b_range.on_change("value", update_b_range)
        images_c_range.on_change("value", update_c_range)
        images_m_range.on_change("value", update_m_range)

        # Marker scale controls
        def increase_marker_size_scale(attr):
            self.marker_size_scale *= 1.5
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        marker_size_scale_inc.on_click(increase_marker_size_scale)

        def decrease_marker_size_scale(attr):
            self.marker_size_scale /= 1.5
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        marker_size_scale_dec.on_click(decrease_marker_size_scale)

        # Marker alpha controls
        def increase_marker_alpha_scale(attr):
            self.marker_alpha_scale *= 1.5
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        marker_alpha_scale_inc.on_click(increase_marker_alpha_scale)

        def decrease_marker_alpha_scale(attr):
            self.marker_alpha_scale /= 1.5
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        marker_alpha_scale_dec.on_click(decrease_marker_alpha_scale)

        # Cabinet scale controls
        def increase_cabinet_scale(attr):
            self.cabinet_scale *= 1.5
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        cabinet_scale_inc.on_click(increase_cabinet_scale)

        def decrease_cabinet_scale(attr):
            self.cabinet_scale /= 1.5
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        cabinet_scale_dec.on_click(decrease_cabinet_scale)

        # Cabinet angle controls
        def increase_cabinet_angle(attr):
            self.cabinet_angle += math.pi / 36.0
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        cabinet_angle_inc.on_click(increase_cabinet_angle)

        def decrease_cabinet_angle(attr):
            self.cabinet_angle -= math.pi / 36.0
            set_configuration(
                structure=self.selected_structure,
                configuration_name=self.selected_configuration_name,
            )

        cabinet_angle_dec.on_click(decrease_cabinet_angle)

        from bokeh.layouts import column, row

        # Controls layout
        c1 = column(
            page_number_div,
            page_number_select,
            configuration_index_div,
            configuration_index_select,
            width=180,
            margin=(0, 20),
        )

        c2 = column(
            images_div,
            row(images_a_range, images_b_range, images_c_range),
            images_m_range,
            width=300,
        )
        c3 = column(
            row(marker_size_scale_div, marker_size_scale_dec, marker_size_scale_inc),
            row(
                marker_alpha_scale_div,
                marker_alpha_scale_dec,
                marker_alpha_scale_inc,
            ),
            row(cabinet_scale_div, cabinet_scale_dec, cabinet_scale_inc),
            row(cabinet_angle_div, cabinet_angle_dec, cabinet_angle_inc),
            width=200,
        )
        c4 = column(
            open_with_button,
            reset_button,
            width=200,
        )

        controls_row = row(c1, c2, c3, c4)

        # Figures grid
        p_xz = view_xz.make_plot()
        p_xz.xaxis.axis_label = "x"
        p_xz.yaxis.axis_label = "z"

        p_yz = view_yz.make_plot()
        p_yz.xaxis.axis_label = "y"
        p_yz.yaxis.axis_label = "z"

        p_xy = view_xy.make_plot()
        p_xy.xaxis.axis_label = "x"
        p_xy.yaxis.axis_label = "y"

        # p_cabinet = view_cabinet.make_plot()
        p_cabinet.xaxis.axis_label = "x (cabinet)"
        p_cabinet.yaxis.axis_label = "z (cabinet)"

        # Overall layout
        layout = column(
            controls_row,
            column(
                row(p_xy, p_cabinet),
                row(p_xz, p_yz),
            ),
            stylesheets=[darkstyle],
        )

        return layout
