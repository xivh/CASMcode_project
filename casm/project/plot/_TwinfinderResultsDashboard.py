import copy
import math
import os
import typing

import bokeh.models
import bokeh.palettes
import numpy as np

import libcasm.xtal as xtal
from casm.twinfinder import (
    TwinfinderResult,
)

from ._ViewAtomicStructure import (
    ViewAtomicStructure,
    make_prim_component_params,
)


class TwinfinderResultsDashboard:
    """Dashboard for viewing ScoredStructureMapping from a
    list[ScoredStructureMapping]"""

    def __init__(
        self,
        results: list[TwinfinderResult],
        component_params: typing.Optional[dict] = None,
        page_size: int = 100,
    ):
        """

        Parameters
        ----------
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

        self.results = results
        """list[casm.twinfinder.TwinfinderResult]: The results to visualize."""

        self._input_component_params = copy.deepcopy(component_params)

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

        self.reset_view()

        # -- Set the initial selection --
        if self.size() != 0:
            self.set_result_index(0)

    def size(self):
        """Return the size of the dashboard"""
        return len(self.results)

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
        if component_params is None and self.size() != 0:
            # Get first record in results:
            result = next(iter(self.results))
            component_params = make_prim_component_params(prim=result.prim)
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
        f = self.selected_image_index / (self.n_images - 1)
        chain_index = self.selected_chain_index

        # Get name
        name = f"Index={result_index}, Equiv={chain_index}, f={f}"

        self.selected_page_number = page_number
        self.options = options
        self.selected_result_index = result_index
        self.selected_result = self.results[result_index]
        self.selected_name = name

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
        s_init = chain[self.selected_image_index]

        a = self.images_a_range
        b = self.images_b_range
        c = self.images_c_range
        m = self.images_m_range
        T = np.diag([a, b, c]) * m
        structure = xtal.make_structure_within(init_structure=s_init)
        superstructure = xtal.make_superstructure(
            transformation_matrix_to_super=T,
            structure=structure,
        )

        self.selected_structure = superstructure

    def make_layout(self, doc=None):
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
            stylesheets=[dark_bk_input_style],
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
            stylesheets=[dark_bk_input_style],
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
            stylesheets=[dark_bk_input_style],
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
            stylesheets=[dark_bk_input_style],
        )

        # Text output:
        def make_invariant_plane_text(plane):
            return f"""<b>Plane:</b> {plane}"""

        def make_shear_direction_text(direction):
            return f"""<b>Direction:</b> {direction}"""

        def make_shear_text(shear):
            return f"""<b>Shear:</b> {shear}"""

        def make_image_symmetry_text(symmetry):
            return f"""<b>Space group:</b> {symmetry}"""

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
        image_symmetry_text = bokeh.models.Div(
            text=make_image_symmetry_text("g"), width=text_width
        )
        cost_text = bokeh.models.Div(
            text=make_cost_text(self.cost_str), width=text_width
        )

        # Open with button:
        open_with_button = bokeh.models.Button(
            label="Open with VESTA", button_type="success"
        )

        # Reset button:
        reset_button = bokeh.models.Button(label="Reset", button_type="success")

        # Run button:
        run_button = bokeh.models.Button(label="► Play", button_type="success")

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
        images_div = bokeh.models.Div(text="""<b># Images</b>""", width=200)
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

        # Set / update the structure being viewed
        # - This updates bokeh data sources for each of the plots based on
        #   the current structure and parameters, so it is also used for
        #   updates to view ranges, cabinet, etc. parameters
        def set_structure(
            structure: xtal.Structure,
            name: str,
        ):
            if self.size() == 0:
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
                title=name,
                new_marker_size_scale=self.marker_size_scale,
                new_marker_alpha_scale=self.marker_alpha_scale,
                new_cabinet=(self.cabinet_scale, self.cabinet_angle),
            )
            invariant_plane_text.text = make_invariant_plane_text(
                self.invariant_plane_str
            )
            shear_direction_text.text = make_shear_direction_text(
                self.shear_direction_str
            )
            shear_text.text = make_shear_text(self.shear_str)
            image_symmetry_text.text = make_image_symmetry_text("g")
            cost_text.text = make_cost_text(self.cost_str)

        if self.selected_structure is not None:
            set_structure(
                structure=self.selected_structure,
                name=self.selected_name,
            )
        p_cabinet = view_cabinet.make_plot()

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

            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )
            p_cabinet.title.text = view_cabinet.title

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

            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )
            p_cabinet.title.text = view_cabinet.title

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

            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )
            p_cabinet.title.text = view_cabinet.title

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

            self.set_image_index(self.selected_image_index)
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        reset_button.on_click(reset_button_action)

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

                set_structure(
                    structure=self.selected_structure.copy(),
                    name=self.selected_name,
                )
                p_cabinet.title.text = view_cabinet.title

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

        # Periodic range - callbacks
        def update_a_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_a_range = new
            self.set_image_index(self.selected_image_index)
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        def update_b_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_b_range = new
            self.set_image_index(self.selected_image_index)
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        def update_c_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_c_range = new
            self.set_image_index(self.selected_image_index)
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        def update_m_range(attr, old, new):
            if self._update_disabled:
                return

            self.images_m_range = new
            self.set_image_index(self.selected_image_index)
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        images_a_range.on_change("value", update_a_range)
        images_b_range.on_change("value", update_b_range)
        images_c_range.on_change("value", update_c_range)
        images_m_range.on_change("value", update_m_range)

        # Marker scale controls
        def increase_marker_size_scale(attr):
            self.marker_size_scale *= 1.5
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        marker_size_scale_inc.on_click(increase_marker_size_scale)

        def decrease_marker_size_scale(attr):
            self.marker_size_scale /= 1.5
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        marker_size_scale_dec.on_click(decrease_marker_size_scale)

        # Marker alpha controls
        def increase_marker_alpha_scale(attr):
            self.marker_alpha_scale *= 1.5
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        marker_alpha_scale_inc.on_click(increase_marker_alpha_scale)

        def decrease_marker_alpha_scale(attr):
            self.marker_alpha_scale /= 1.5
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        marker_alpha_scale_dec.on_click(decrease_marker_alpha_scale)

        # Cabinet scale controls
        def increase_cabinet_scale(attr):
            self.cabinet_scale *= 1.5
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        cabinet_scale_inc.on_click(increase_cabinet_scale)

        def decrease_cabinet_scale(attr):
            self.cabinet_scale /= 1.5
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        cabinet_scale_dec.on_click(decrease_cabinet_scale)

        # Cabinet angle controls
        def increase_cabinet_angle(attr):
            self.cabinet_angle += math.pi / 36.0
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        cabinet_angle_inc.on_click(increase_cabinet_angle)

        def decrease_cabinet_angle(attr):
            self.cabinet_angle -= math.pi / 36.0
            set_structure(
                structure=self.selected_structure.copy(),
                name=self.selected_name,
            )

        cabinet_angle_dec.on_click(decrease_cabinet_angle)

        from bokeh.layouts import column, row

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
            run_button,
            width=200,
        )

        c5 = column(
            invariant_plane_text,
            shear_direction_text,
            shear_text,
            image_symmetry_text,
            cost_text,
            width=600,
        )

        controls_row = row(c1, column(row(c2, c3, c4), row(c5)))

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
