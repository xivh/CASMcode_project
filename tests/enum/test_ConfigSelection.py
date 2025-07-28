import numpy as np

import casm.project
from casm.project.enum import ConfigSelection, ConfigSelectionRecord


def setup_SiGe_occ(project, enum_id="main"):
    ## Select project composition axes ##

    project.chemical_composition_axes.set_current_axes(1)
    project.chemical_composition_axes.commit()
    project.occupant_composition_axes.set_current_axes(1)
    project.occupant_composition_axes.commit()

    # Specify the basis set ID
    # - Must be alphanumeric and underscores only
    bset_id = "default"

    ## Construct the basis set specs ##

    # Specify maximum cluster site-to-site distance,
    # by number of sites in the cluster
    pair_max_length = 10.01
    triplet_max_length = 7.27
    quad_max_length = 4.0

    # Use chebychev site basis functions (+x, -x)
    occ_site_basis_functions_specs = "occupation"

    bset = project.bset.get(bset_id)
    bset.make_bspecs(
        max_length=[
            0.0,  # null cluster, arbitrary
            0.0,  # point cluster, arbitrary
            pair_max_length,
            triplet_max_length,
            quad_max_length,
        ],
        occ_site_basis_functions_specs=occ_site_basis_functions_specs,
    )
    bset.commit()  # <-- Save the basis set specs
    bset.update()  # <-- Write & compile the clexulator

    ## Enumerate configurations ##

    enum = project.enum.get(enum_id)
    enum.occ_by_supercell(max=4, min=1)


def check_attr_types(config_selection):
    """Check the types of attributes in ConfigSelection records.

    These checks require composition axes and a basis set for the default clex.
    """

    for record in config_selection:
        assert isinstance(record, ConfigSelectionRecord)
        # print("Record:")
        # print("- name:", record.name)
        assert isinstance(record.name, str)

        # print("- source:", record.source)
        assert isinstance(record.source, str)

        # print("- configuration:", record.configuration)
        assert isinstance(
            record.configuration, object
        )  # Replace `object` with the specific type if known

        # print("- chemical_param_comp:", record.chemical_param_comp)
        assert isinstance(record.chemical_param_comp, np.ndarray)

        # print("- chemical_comp_per_supercell:", record.chemical_comp_per_supercell)
        assert isinstance(record.chemical_comp_per_supercell, np.ndarray)

        # print("- chemical_comp_per_unitcell:", record.chemical_comp_per_unitcell)
        assert isinstance(record.chemical_comp_per_unitcell, np.ndarray)

        # print("- occupant_param_comp:", record.occupant_param_comp)
        assert isinstance(record.occupant_param_comp, np.ndarray)

        # print("- occupant_comp_per_supercell:", record.occupant_comp_per_supercell)
        assert isinstance(record.occupant_comp_per_supercell, np.ndarray)

        # print("- occupant_comp_per_unitcell:", record.occupant_comp_per_unitcell)
        assert isinstance(record.occupant_comp_per_unitcell, np.ndarray)

        # print("- corr_per_supercell:", record.corr_per_supercell)
        assert isinstance(record.corr_per_supercell, np.ndarray)

        # print("- corr_per_unitcell:", record.corr_per_unitcell)
        assert isinstance(record.corr_per_unitcell, np.ndarray)

        # print()


def test_ConfigSelection_SiGe_1(SiGe_occ_tmp_project):
    project = SiGe_occ_tmp_project
    assert isinstance(project, casm.project.Project)
    project.sym.print_factor_group()

    enum_id = "main"
    setup_SiGe_occ(project, enum_id=enum_id)

    ## Test ConfigSelection ##

    sel_id = "main"

    enum = project.enum.get(enum_id)
    config_selection = ConfigSelection(
        enum=enum,
        name=sel_id,
    )
    assert isinstance(config_selection, ConfigSelection)
    assert len(config_selection) == 214

    check_attr_types(config_selection)

    expected_path = enum.enum_dir / f"config_selection.{sel_id}.json"
    assert config_selection.path == expected_path
    assert config_selection.path.exists() is False
    config_selection.commit()  # <-- Save the configuration selection
    assert config_selection.path.exists() is True

    config_selection_in = ConfigSelection(
        enum=enum,
        name=sel_id,
    )
    assert isinstance(config_selection_in, ConfigSelection)
    assert len(config_selection_in) == 214


def test_ConfigSelection_iter(SiGe_occ_tmp_project):
    project = SiGe_occ_tmp_project
    assert isinstance(project, casm.project.Project)

    enum_id = "main"
    enum = project.enum.get(enum_id)
    enum.occ_by_supercell(max=4, min=1)

    sel = enum.config_selection("main")
    sel.set_selected(lambda record: record.n_unitcells == 2)

    assert len(sel) == 214
    count = 0
    for record in sel:
        if record.is_selected:
            count += 1
    assert count == 7

    # Iterate through the selected configurations
    count = 0
    for record in sel:
        count += 1
    assert count == 7

    # Also iterate through the selected configurations
    count = 0
    for record in sel.selected:
        count += 1
    assert count == 7

    # Iterate through the unselected configurations
    count = 0
    for record in sel.unselected:
        count += 1
    assert count == 207

    # Iterate through all configurations
    count = 0
    for record in sel.all:
        count += 1
    assert count == 214


def test_ConfigSelection_SiGe_2(SiGe_occ_tmp_project):
    project = SiGe_occ_tmp_project
    assert isinstance(project, casm.project.Project)
    project.sym.print_factor_group()

    enum_id = "main"
    setup_SiGe_occ(project, enum_id=enum_id)

    ## Test ConfigSelection ##

    sel_id = "main"
    enum = project.enum.get(enum_id)
    config_selection = enum.config_selection(
        name=sel_id,
    )
    assert isinstance(config_selection, ConfigSelection)
    assert len(config_selection) == 214
    check_attr_types(config_selection)
