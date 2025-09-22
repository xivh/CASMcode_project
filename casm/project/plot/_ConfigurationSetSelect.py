import typing

import bokeh.models
from bokeh.layouts import column, row

import libcasm.configuration as casmconfig

from ._DashboardStyles import DashboardStyles


class ConfigurationSetSelect:

    def __init__(
        self,
        configuration_set: casmconfig.ConfigurationSet,
        parent: typing.Any,
    ):
        self.configuration_set = configuration_set
        self.parent = parent

        self._disable_update = False

        ### Data preparation - begin ###

        supercell_name = []
        configuration_id_by_supercell_name = {}

        for record in self.configuration_set:
            if record.supercell_name not in supercell_name:
                supercell_name.append(record.supercell_name)
                configuration_id_by_supercell_name[record.supercell_name] = []
            configuration_id_by_supercell_name[record.supercell_name].append(
                record.configuration_id
            )
        supercell_name.sort()
        for key, value in configuration_id_by_supercell_name.items():
            value.sort(key=lambda x: int(x))
        if len(supercell_name) > 0:
            self.supercell_name_options = supercell_name
            self.config_id_options = configuration_id_by_supercell_name
        else:
            self.supercell_name_options = ["(None)"]
            self.config_id_options = {"(None)": ["(None)"]}
        self.i_supercell = 0
        self.i_config = 0

        ### Data preparation - end ###

        self.set_structure()

    def set_structure(self):
        supercell_name = self.supercell_name_options[self.i_supercell]
        config_id_options = self.config_id_options[supercell_name]
        config_id = config_id_options[self.i_config]
        configuration_name = supercell_name + "/" + config_id
        record = self.configuration_set.get_by_name(configuration_name)
        if record is None:
            raise Exception("Configuration not found: " + configuration_name)
        structure = record.configuration.to_structure(excluded_species=[])

        self.parent.selected_structure = structure
        self.parent.selected_structure_name = configuration_name

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
            text="""<b>ConfigurationSet</b>""", width=200
        )
        supercell_name_value = self.supercell_name_options[self.i_supercell]
        config_id_options = self.config_id_options[supercell_name_value]
        config_id_value = config_id_options[self.i_config]

        supercell_name_select = bokeh.models.Select(
            options=self.supercell_name_options,
            value=supercell_name_value,
            stylesheets=[styles.dark_bk_input_style],
            title="Supercell name",
        )
        config_id_select = bokeh.models.Select(
            options=config_id_options,
            value=config_id_value,
            stylesheets=[styles.dark_bk_input_style],
            title="Configuration ID",
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
        def _supercell_name_callback(attr, old, new):
            if self._disable_update:
                return

            self._disable_update = True
            supercell_name_select.value = new
            self.i_supercell = self.supercell_name_options.index(new)
            config_id_select.options = self.config_id_options[new]
            config_id_select.value = self.config_id_options[new][0]
            self.i_config = 0
            self._disable_update = False

            self.update()

        supercell_name_select.on_change("value", _supercell_name_callback)

        def _config_id_callback(attr, old, new):
            if self._disable_update:
                return

            config_id_select.value = new
            self.i_config = config_id_select.options.index(new)

            self.update()

        config_id_select.on_change("value", _config_id_callback)

        def _iterate_inc_callback(attr):
            self._disable_update = True
            if self.i_config == len(config_id_select.options) - 1:
                if self.i_supercell == len(supercell_name_select.options) - 1:
                    self._disable_update = False
                    return
                else:
                    self.i_supercell += 1
                supercell_name_value = self.supercell_name_options[self.i_supercell]

                config_id_options = self.config_id_options[supercell_name_value]
                self.i_config = 0
                config_id_select.options = config_id_options
                config_id_select.value = config_id_options[self.i_config]
            else:
                supercell_name_value = self.supercell_name_options[self.i_supercell]
                self.i_config += 1
                config_id_options = self.config_id_options[supercell_name_value]
                config_id_select.value = config_id_options[self.i_config]
            self._disable_update = False

            self.update()

        iterate_inc.on_click(_iterate_inc_callback)

        def _iterate_dec_callback(attr):
            self._disable_update = True
            if self.i_config == 0:
                if self.i_supercell == 0:
                    self._disable_update = False
                    return
                else:
                    self.i_supercell -= 1
                supercell_name_value = self.supercell_name_options[self.i_supercell]

                config_id_options = self.config_id_options[supercell_name_value]
                self.i_config = len(config_id_options) - 1
                config_id_select.options = config_id_options
                config_id_select.value = config_id_options[self.i_config]
            else:
                supercell_name_value = self.supercell_name_options[self.i_supercell]
                self.i_config -= 1
                config_id_options = self.config_id_options[supercell_name_value]
                config_id_select.value = config_id_options[self.i_config]
            self._disable_update = False

            self.update()

        iterate_dec.on_click(_iterate_dec_callback)

        ### Callbacks - end ###

        # Configuration selection:
        c1 = column(
            # self.configuration_set_div,
            row(
                supercell_name_select,
                config_id_select,
                iterate_div,
                iterate_dec,
                iterate_inc,
                sizing_mode="stretch_width",
            ),
            margin=(10, 20),
        )
        return row(c1)
