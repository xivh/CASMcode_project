import os
import typing

import bokeh.models
import bokeh.palettes
import numpy as np
from bokeh.layouts import column, row

import libcasm.configuration as casmconfig
from casm.twinfinder import TwinfinderResult

from ._DashboardStyles import DashboardStyles
from ._ProjectionView import ProjectionView
from ._ViewControl import ViewControl


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
