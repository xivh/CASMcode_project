import typing

import bokeh.models
from bokeh.layouts import column, row

import libcasm.configuration as casmconfig

from ._DashboardStyles import DashboardStyles


class ConfigurationListSelect:

    def __init__(
        self,
        configuration_list: list[casmconfig.Configuration],
        parent: typing.Any,
    ):
        self.configuration_list = configuration_list
        self.parent = parent
        self.page_size = 100
        self.i_page = None
        self.i_index_on_page = None

        self._disable_update = False

        ### Data preparation - begin ###

        if len(self.configuration_list) > 0:

            def make_label(i):
                # page 1: (0-99)
                # page 2: (100-199)
                # etc.
                begin = (i - 1) * self.page_size
                end = i * self.page_size - 1
                return f"Pg. {i}: ({begin}-{end})"

            i_page = 0

            page_number_options = [(i_page, make_label(i_page + 1))]
            config_index_by_page_number = {i_page: []}

            i_config = 0
            i_index_on_page = 0
            for config in self.configuration_list:
                i_config_str = str(i_config)
                if i_index_on_page == self.page_size:
                    i_page += 1
                    i_index_on_page = 0
                    page_number_options.append((i_page, make_label(i_page + 1)))
                    config_index_by_page_number[i_page] = []
                config_index_by_page_number[i_page].append(i_config_str)
                i_config += 1
                i_index_on_page += 1

            self.i_page = 0
            self.i_index_on_page = 0

        else:
            page_number_options = ["(None)"]
            config_index_by_page_number = {"(None)": ["(None)"]}

        self.page_number_options = page_number_options
        self.config_index_by_page_number = config_index_by_page_number

        ### Data preparation - end ###

        self.set_structure()

    def set_structure(self):
        config_index = int(
            self.config_index_by_page_number[self.i_page][self.i_index_on_page]
        )
        configuration = self.configuration_list[config_index]
        structure = configuration.to_structure(excluded_species=[])

        self.parent.selected_structure = structure
        self.parent.selected_structure_name = f"config_list/{config_index}"

    def update(
        self,
    ):
        self.set_structure()
        self.parent.trigger_update()

    def make_layout(
        self,
        styles: DashboardStyles = None,
    ):
        ### Widgets construction - begin ###

        self.configuration_set_div = bokeh.models.Div(
            text="""<b>Configuration list</b>""", width=200
        )
        page_number_select = bokeh.models.Select(
            options=self.page_number_options,
            value=self.i_page,
            stylesheets=[styles.dark_bk_input_style],
            title="Page Number",
        )
        config_index_select = bokeh.models.Select(
            options=self.config_index_by_page_number[self.i_page],
            value=self.config_index_by_page_number[self.i_page][self.i_index_on_page],
            stylesheets=[styles.dark_bk_input_style],
            title="Configuration Index",
        )
        # Marker scale controls
        iterate_div = bokeh.models.Div(text="""Iterate:&nbsp;&nbsp;""")
        iterate_inc = bokeh.models.Button(
            label="+", stylesheets=[styles.dark_bk_input_style]
        )
        iterate_dec = bokeh.models.Button(
            label="-", stylesheets=[styles.dark_bk_input_style]
        )

        ### Widgets construction - end ###

        ### Callbacks - begin ###
        def _page_number_callback(attr, old, new):
            if self._disable_update:
                return

            self._disable_update = True
            page_number_select.value = new
            self.i_page = new
            self.i_index_on_page = 0
            options = self.config_index_by_page_number[new]
            config_index_select.options = options
            config_index_select.value = options[self.i_index_on_page]
            self._disable_update = False

            self.update()

        page_number_select.on_change("value", _page_number_callback)

        def _config_index_callback(attr, old, new):
            if self._disable_update:
                return

            config_index_select.value = new
            self.i_index_on_page = config_index_select.options.index(new)

            self.update()

        config_index_select.on_change("value", _config_index_callback)

        def _iterate_inc_callback(attr):
            self._disable_update = True
            if self.i_index_on_page == len(config_index_select.options) - 1:
                if self.i_page == len(page_number_select.options) - 1:
                    self._disable_update = False
                    return
                else:
                    self.i_page += 1
                page_number_select.value = self.i_page

                options = self.config_index_by_page_number[self.i_page]
                self.i_index_on_page = 0
                config_index_select.options = options
                config_index_select.value = options[self.i_index_on_page]
            else:
                self.i_index_on_page += 1
                options = self.config_index_by_page_number[self.i_page]
                config_index_select.value = options[self.i_index_on_page]
            self._disable_update = False

            self.update()

        iterate_inc.on_click(_iterate_inc_callback)

        def _iterate_dec_callback(attr):
            self._disable_update = True
            if self.i_index_on_page == 0:
                if self.i_page == 0:
                    self._disable_update = False
                    return
                else:
                    self.i_page -= 1
                page_number_select.value = self.i_page

                options = self.config_index_by_page_number[self.i_page]
                self.i_index_on_page = len(options) - 1
                config_index_select.options = options
                config_index_select.value = options[self.i_index_on_page]
            else:
                self.i_index_on_page -= 1
                options = self.config_index_by_page_number[self.i_page]
                config_index_select.value = options[self.i_index_on_page]
            self._disable_update = False

            self.update()

        iterate_dec.on_click(_iterate_dec_callback)

        ### Callbacks - end ###

        # Configuration selection:
        c1 = column(
            # self.configuration_set_div,
            row(
                page_number_select,
                config_index_select,
                iterate_div,
                iterate_dec,
                iterate_inc,
                sizing_mode="stretch_width",
            ),
            margin=(10, 20),
        )
        return row(c1)
