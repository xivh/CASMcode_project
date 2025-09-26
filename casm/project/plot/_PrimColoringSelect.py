import typing

import bokeh.models
from bokeh.layouts import column, row

import libcasm.clusterography as casmclust
import libcasm.configuration as casmconfig
import libcasm.sym_info as sym_info
import libcasm.xtal as xtal
from libcasm.configuration.io import symgroup_to_dict_with_group_classification

from ._DashboardStyles import DashboardStyles
from ._ViewAtomicStructure import (
    make_prim_component_params,
)


def make_site_groups(
    prim: casmconfig.Prim,
):
    """Make site groups for each site in the primitive cell.

    Parameters
    ----------
    prim: libcasm.configuration.Prim
        The primitive cell.

    Returns
    -------
    list[libcasm.sym_info.SymGroup]
        The site groups for each site in the primitive cell.
    """
    site_groups = []
    rep = casmclust.make_integral_site_coordinate_symgroup_rep(
        group_elements=prim.factor_group.elements,
        xtal_prim=prim.xtal_prim,
    )
    for b, site_occ_dof in enumerate(prim.xtal_prim.occ_dof()):
        cluster = casmclust.Cluster.from_list([[b, 0, 0, 0]])
        cluster_group = casmclust.make_cluster_group(
            cluster=cluster,
            group=prim.factor_group,
            lattice=prim.xtal_prim.lattice(),
            integral_site_coordinate_symgroup_rep=rep,
        )
        site_groups.append(cluster_group)
    return site_groups


def make_site_groups_data(
    site_groups: list[sym_info.SymGroup],
    prim: casmconfig.Prim,
):
    lattice = prim.xtal_prim.lattice()
    site_groups_data = []
    for b, site_group in enumerate(site_groups):
        data = symgroup_to_dict_with_group_classification(
            obj=lattice,
            symgroup=site_group,
        )
        site_groups_data.append(data)
    return site_groups_data


def make_component_params(
    components: list[str],
):

    components = list(set(components))  # unique
    components.sort()

    if len(components) > 10:
        raise ValueError("Error in make_component_params: " "> 10 unique components")
    # Use bokeh color palette Set1:
    component_params = {}
    for i, _body_name in enumerate(components):
        color = bokeh.palettes.Category10_10[i % 10]
        component_params[_body_name] = dict(
            color=color,
            size=30.0,
            alpha=0.8,
            line_color="black",
            line_width=0.25,
            line_dash="solid",
        )
    return component_params


def add_line_component_params(
    component_params: dict,
    line_color_components: list[str],
):
    line_color_components = list(set(line_color_components))  # unique
    line_color_components.sort()

    if len(line_color_components) > 10:
        raise ValueError(
            "Error in add_line_component_params: " "> 10 unique line color components"
        )

    new_component_params = dict(component_params)  # copy

    for name, params in component_params.items():
        new_params = dict(params)
        for j, _line_name in enumerate(line_color_components):
            line_color = bokeh.palettes.Category10_10[j % 10]
            new_params["line_color"] = line_color
            new_component_params[name + "_" + _line_name] = new_params
    return new_component_params


def make_highlight_params(
    prim_component_params: dict,
    highlight_color: str,
    highlight_width: float = 2.0,
):
    highlight_params = dict(prim_component_params)

    for name, params in highlight_params.items():
        params["line_alpha"] = 1.0

    for name, params in prim_component_params.items():

        new_params = dict(params)
        new_params["line_color"] = highlight_color
        new_params["line_width"] = highlight_width
        new_params["line_alpha"] = 1.0
        highlight_params[name + "_sel"] = new_params
    return highlight_params


class PrimColoringSelect:

    def __init__(
        self,
        prim: casmconfig.Prim,
        parent: typing.Any,
    ):
        self.prim = prim
        self.parent = parent

        self._disable_update = False
        self._prim_component_params = make_prim_component_params(prim=self.prim)

        ### Data preparation - begin ###

        self.asymmetric_unit_indices = xtal.asymmetric_unit_indices(self.prim.xtal_prim)

        self.sublattice_data = []

        labels = self.prim.xtal_prim.labels()
        coordinate_cart = self.prim.xtal_prim.coordinate_cart()
        coordinate_frac = self.prim.xtal_prim.coordinate_frac()
        occ_dof = self.prim.xtal_prim.occ_dof()
        local_dof = self.prim.xtal_prim.local_dof()
        occupants = self.prim.xtal_prim.occupants()
        n_sites = len(labels)

        # Make a list of non-equivalent site names
        site_names = [-1] * n_sites
        unique_site_names = []
        for i_asym, sublats in enumerate(self.asymmetric_unit_indices):
            name = f"s{i_asym+1}"
            unique_site_names.append(name)
            for b in sublats:
                site_names[b] = name
        self.unique_site_names = unique_site_names
        self.site_names = site_names

        # Make a list of chemical names
        unique_chemical_names = []
        for id, occupant in occupants.items():
            if occupant.name() not in unique_chemical_names:
                unique_chemical_names.append(occupant.name())
        unique_chemical_names.sort()
        self.unique_chemical_names = unique_chemical_names

        # Make site groups
        self.site_groups = make_site_groups(prim=self.prim)
        self.site_groups_data = make_site_groups_data(
            site_groups=self.site_groups,
            prim=self.prim,
        )

        for b, site_occ_dof in enumerate(occ_dof):
            data = dict()

            # Labels
            data["sublattice"] = b
            data["label"] = labels[b]
            for i_asym, sublats in enumerate(self.asymmetric_unit_indices):
                if b in sublats:
                    data["asymmetric_unit_index"] = i_asym
                    data["site_name"] = f"s{i_asym+1}"
                    break
            else:
                raise Exception("Site not found in any asymmetric unit index.")

            # Coordinates
            data["coordinate_cart"] = coordinate_cart[:, b]
            data["coordinate_frac"] = coordinate_frac[:, b]

            # Occupants
            data["default_occ"] = site_occ_dof[0]
            data["default_chemical_name"] = occupants[site_occ_dof[0]].name()
            data["occ_dof"] = site_occ_dof
            data["occ_dof_chemical_name"] = [occupants[x].name() for x in site_occ_dof]
            data["local_dof"] = [x.dofname() for x in local_dof[b]]

            # Site symmetry
            grpcls = self.site_groups_data[b]["group_classification"]
            if "spacegroup_type_from_casm_symmetry" in grpcls:
                symdata = grpcls["spacegroup_type_from_casm_symmetry"]
            else:
                symdata = grpcls["spacegroup_type"]

            data["pointgroup_international"] = symdata["pointgroup_international"]
            data["pointgroup_schoenflies"] = symdata["pointgroup_schoenflies"]

            # Append to list
            self.sublattice_data.append(data)

        self.cp = dict()
        """dict[str, dict]: Component parameters for each property."""

        self.keys = [
            "none",
            "site_name",
            "default_occ",
            "default_chemical_name",
            "occ_dof",
            "occ_dof_chemical_name",
            "local_dof",
            "pointgroup_international",
            "pointgroup_schoenflies",
        ]

        self.attr_type = {
            "none": None,
            "site_name": "str",
            "default_occ": "str",
            "default_chemical_name": "str",
            "occ_dof": "list_str",
            "occ_dof_chemical_name": "list_str",
            "local_dof": "list_str",
            "pointgroup_international": "str",
            "pointgroup_schoenflies": "str",
        }

        self.attr_values = dict()
        for key in self.keys:
            if key == "none":
                components = ["(None)"]
            else:
                if self.attr_type[key] == "str":
                    components = list(set([data[key] for data in self.sublattice_data]))
                elif self.attr_type[key] == "list_str":
                    components = ["(None)"]
                    for data in self.sublattice_data:
                        for item in data[key]:
                            if item not in components:
                                components.append(item)
                else:
                    raise ValueError(f"Unknown attr_type: {self.attr_type[key]}")
                components.sort()
            self.attr_values[key] = components

        self.labels = {
            "none": "(None)",
            "site_name": "Equivalent sites",
            "default_occ": "Default occupant",
            "default_chemical_name": "Default occupant (chemical name)",
            "occ_dof": "Allowed occupant",
            "occ_dof_chemical_name": "Allowed occupant (chemical name)",
            "local_dof": "Continuous DoF",
            "pointgroup_international": "Site symmetry (International)",
            "pointgroup_schoenflies": "Site symmetry (Schoenflies)",
        }

        ### Data preparation - end ###

        self.current_key = "none"
        self.current_attr_values = dict()
        for key in self.keys:
            self.current_attr_values[key] = self.attr_values[key][0]
        self.current_color = "cyan"
        self.current_width = 5.0
        self.set_structure()

    def set_structure(self):

        key = self.current_key
        selected_value = self.current_attr_values[key]
        highlight_color = self.current_color
        highlight_width = self.current_width

        psuedo_atom_type = []
        attr_type = self.attr_type[key]
        if attr_type is None:
            for data in self.sublattice_data:
                psuedo_atom_type.append(data["default_chemical_name"])
        elif attr_type == "str":
            if selected_value is None:
                raise ValueError(
                    "selected_value must be provided when key is not 'none'"
                )
            for data in self.sublattice_data:
                _name = data["default_chemical_name"]
                if data[key] == selected_value:
                    _name += "_sel"
                psuedo_atom_type.append(_name)
        elif attr_type == "list_str":
            if selected_value is None:
                raise ValueError(
                    "selected_value must be provided when key is not 'none'"
                )
            for data in self.sublattice_data:
                _name = data["default_chemical_name"]
                if selected_value == "(None)":
                    if len(data[key]) == 0:
                        _name += "_sel"
                elif selected_value in data[key]:
                    _name += "_sel"
                psuedo_atom_type.append(_name)

        structure = xtal.Structure(
            lattice=self.prim.xtal_prim.lattice(),
            atom_coordinate_frac=self.prim.xtal_prim.coordinate_frac(),
            atom_type=psuedo_atom_type,
        )

        component_params = make_highlight_params(
            prim_component_params=make_prim_component_params(prim=self.prim),
            highlight_color=highlight_color,
            highlight_width=highlight_width,
        )

        self.parent.view_control.reset_component_params(
            component_params=component_params
        )
        self.parent.selected_structure = structure

        if key == "none":
            name = "Prim"
        else:
            name = f"Prim, {self.labels[key]}={selected_value}"
        self.parent.selected_structure_name = name

    def update(self):
        self.set_structure()
        self.parent.trigger_update()

    def make_layout(
        self,
        styles: DashboardStyles = None,
    ):
        ### Widgets construction - begin ###

        highlight_colorpicker = bokeh.models.ColorPicker(
            title="Color",
            color=self.current_color,
            width=50,
            stylesheets=[styles.dark_bk_input_style],
        )
        highlight_width_spinner = bokeh.models.Spinner(
            title="Width",
            low=-0.01,
            high=100.01,
            step=0.5,
            value=self.current_width,
            width=70,
            stylesheets=[styles.dark_bk_input_style],
        )

        attr_select = bokeh.models.Select(
            options=[(key, self.labels[key]) for key in self.keys],
            value=self.current_key,
            stylesheets=[styles.dark_bk_input_style],
            title="Highlight",
        )

        attr_value_select = dict()
        all_value_select = []
        for key in self.keys:

            select = bokeh.models.Select(
                options=self.attr_values[key],
                value=str(self.current_attr_values[key]),
                stylesheets=[styles.dark_bk_input_style],
                title="Value",
                visible=self.current_key == key,
            )

            attr_value_select[key] = select
            all_value_select.append(select)

        ### Widgets construction - end ###

        ### Callbacks - begin ###

        for select in all_value_select:

            def _callback(attr, old, new):
                if self._disable_update:
                    return

                self._disable_update = True
                self.current_attr_values[self.current_key] = new
                self._disable_update = False

                self.update()

            select.on_change("value", _callback)

        def _coloring_by_callback(attr, old, new):
            if self._disable_update:
                return

            self._disable_update = True
            self.current_key = new
            for key, value_select in attr_value_select.items():
                value_select.visible = key == new
            self._disable_update = False

            self.update()

        attr_select.on_change("value", _coloring_by_callback)

        def _highlight_color_callback(attr, old, new):
            if self._disable_update:
                return

            self._disable_update = True
            self.current_color = new
            self._disable_update = False

            self.update()

        highlight_colorpicker.on_change("color", _highlight_color_callback)

        def _highlight_width_callback(attr, old, new):
            if self._disable_update:
                return

            self._disable_update = True
            self.current_width = new
            self._disable_update = False

            self.update()

        highlight_width_spinner.on_change("value", _highlight_width_callback)

        ### Callbacks - end ###

        value_select_col = column(
            *all_value_select,
        )

        # Configuration selection:
        c1 = column(
            row(
                attr_select,
                value_select_col,
                highlight_colorpicker,
                highlight_width_spinner,
                sizing_mode="stretch_width",
            ),
            margin=(10, 20),
        )
        return row(c1)
