import os
import pathlib
import tempfile
from typing import Optional, Union

import numpy as np
import pytest

import libcasm.configuration as casmconfig
from casm.project import (
    Project,
)
from casm.project.json_io import read_required

repo_dir = pathlib.Path(os.path.abspath(__file__)).parent.parent
prim_dir = repo_dir / "notebooks" / "input" / "prim"


def periodic_project_checks(
    prim: casmconfig.Prim,
    max_length: list[float],
    occ_site_basis_functions_specs: Union[str, list[dict], None],
    global_max_poly_order: Optional[int] = None,
):
    tmpdir = tempfile.TemporaryDirectory()
    project_path = pathlib.Path(tmpdir.name)
    project = Project.init(
        path=project_path,
        prim=prim,
    )
    assert isinstance(project, Project)

    ## Enum occupations ##
    enum_id = "occ_by_supercell.1"
    enum = project.enum.get(enum_id)
    enum.occ_by_supercell(max=4)
    n_config = len(enum.configuration_set)
    print("n_config", n_config)

    ## Get compositions ##
    comp_calculator = project.make_chemical_comp_calculator()
    n_components = comp_calculator.n_components
    k = project.chemical_composition_axes.independent_compositions
    print("Composition axes: (chemical)")
    print(f"- components: {comp_calculator.components}")
    print(f"- n_chemical_components: {n_components}")
    print(f"- independent_compositions: {k}")
    print(f"- n_possible_axes: {len(project.chemical_composition_axes.possible_axes)}")
    print()

    comp_n = comp_calculator.per_unitcell(enum.configuration_set)
    assert isinstance(comp_n, np.ndarray)
    assert comp_n.shape == (n_config, n_components)

    comp_N = comp_calculator.per_supercell(enum.configuration_set)
    assert isinstance(comp_N, np.ndarray)
    assert comp_N.shape == (n_config, n_components)

    species_frac = comp_calculator.species_frac(enum.configuration_set)
    assert isinstance(species_frac, np.ndarray)
    assert species_frac.shape == (n_config, n_components)

    if k > 0:
        project.chemical_composition_axes.set_current_axes("0")
        comp_calculator = project.make_chemical_comp_calculator()
        assert k == comp_calculator.independent_compositions
        param_composition = comp_calculator.param_composition(enum.configuration_set)
        assert isinstance(param_composition, np.ndarray)
        assert param_composition.shape == (n_config, k)

    comp_calculator_occ = project.make_occupant_comp_calculator()
    if comp_calculator.components != comp_calculator_occ.components:
        n_components_occ = comp_calculator_occ.n_components
        k_occ = project.occupant_composition_axes.independent_compositions

        print("Composition axes: (occupant)")
        print(f"- components: {comp_calculator_occ.components}")
        print(f"- n_components: {n_components_occ}")
        print(f"- independent_compositions: {k_occ}")
        print(
            f"- n_possible_axes: {len(project.occupant_composition_axes.possible_axes)}"
        )
        print()

        comp_n = comp_calculator_occ.per_unitcell(enum.configuration_set)
        assert isinstance(comp_n, np.ndarray)
        assert comp_n.shape == (n_config, n_components_occ)

        comp_N = comp_calculator_occ.per_supercell(enum.configuration_set)
        assert isinstance(comp_N, np.ndarray)
        assert comp_N.shape == (n_config, n_components_occ)

        species_frac = comp_calculator_occ.species_frac(enum.configuration_set)
        assert isinstance(species_frac, np.ndarray)
        assert species_frac.shape == (n_config, n_components_occ)

        if k_occ > 0:
            project.occupant_composition_axes.set_current_axes("0")
            comp_calculator_occ = project.make_occupant_comp_calculator()
            assert k_occ == comp_calculator_occ.independent_compositions
            param_composition = comp_calculator_occ.param_composition(
                enum.configuration_set
            )
            assert isinstance(param_composition, np.ndarray)
            assert param_composition.shape == (n_config, k_occ)

    ## Construct the basis set specs ##
    bset_id = "default"
    bset = project.bset.get(bset_id)
    bset.make_bspecs(
        max_length=max_length,
        occ_site_basis_functions_specs=occ_site_basis_functions_specs,
        global_max_poly_order=global_max_poly_order,
    )
    bset.commit()
    bset.update(verbose=True, very_verbose=False)
    assert project.dir.clexulator_src(projectname=project.name, bset=bset_id).exists()

    ## Evaluate correlations
    corr_calculator = bset.make_corr_calculator()
    n_functions = corr_calculator.n_functions
    print("n_functions", n_functions)

    corr = corr_calculator.per_unitcell(enum.configuration_set)
    assert isinstance(corr, np.ndarray)
    assert corr.shape == (n_config, n_functions)


# def test_prims():
#     prim_dir = repo_dir / "notebooks" / "input" / "prim"
#     for prim_file in prim_dir.glob("*_prim.json"):
#         print("Testing", prim_file)
#         data = read_required(prim_file)
#         prim = casmconfig.Prim.from_dict(data=data)
#         periodic_project_checks(prim)
#         print()


def test_ZrO_prim():
    name = "ZrO_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 10.01, 8.01, 4.01],
        occ_site_basis_functions_specs="chebychev",
    )


def test_SiGe_occ_prim():
    name = "SiGe_occ_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 10.01, 8.01, 4.01],
        occ_site_basis_functions_specs="chebychev",
    )


def test_SiGe_occ_Hstrain_prim():
    name = "SiGe_occ_Hstrain_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 10.01, 8.01, 4.01],
        occ_site_basis_functions_specs="chebychev",
    )


def test_FCC_ternary_prim():
    name = "FCC_ternary_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 8.01, 6.01, 4.01],
        occ_site_basis_functions_specs="chebychev",
    )


def test_FCC_ternary_prim_null():
    name = "FCC_ternary_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0],
        occ_site_basis_functions_specs="chebychev",
    )


def test_FCC_Hstrain_prim():
    name = "FCC_Hstrain_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0],
        occ_site_basis_functions_specs=None,
        global_max_poly_order=3,
    )


def test_FCC_Hstrain_prim_null():
    name = "FCC_Hstrain_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0],
        occ_site_basis_functions_specs=None,
        global_max_poly_order=0,
    )


def test_FCC_disp_prim():
    name = "FCC_disp_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 4.01, 2.9, 2.9],
        occ_site_basis_functions_specs=None,
    )


def test_FCC_Cmagspin_prim():
    name = "FCC_Cmagspin_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 8.01, 6.01, 4.01],
        occ_site_basis_functions_specs="chebychev",
    )


def test_FCC_Cmagspin_prim_occ():
    name = "FCC_Cmagspin_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))

    with pytest.raises(
        ValueError, match="Invalid choice of occupation DoF site basis functions."
    ):
        periodic_project_checks(
            prim=prim,
            max_length=[0.0, 0.0, 8.01, 6.01, 4.01],
            occ_site_basis_functions_specs="occupation",
        )


def test_FCC_binary_Cmagspin_prim():
    name = "FCC_binary_Cmagspin_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 10.01, 8.01, 4.01],
        occ_site_basis_functions_specs="chebychev",
    )


def test_FCC_mol_prim():
    name = "FCC_mol_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 8.01, 6.01, 4.01],
        occ_site_basis_functions_specs="chebychev",
    )


def test_FCC_mol_prim_occ():
    name = "FCC_mol_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))

    with pytest.raises(
        ValueError, match="Invalid choice of occupation DoF site basis functions."
    ):
        periodic_project_checks(
            prim=prim,
            max_length=[0.0, 0.0, 8.01, 6.01, 4.01],
            occ_site_basis_functions_specs="occupation",
        )


def test_FCC_mol_prim_comp():
    name = "FCC_mol_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))

    with pytest.raises(
        ValueError, match="Invalid choice of occupation DoF site basis functions."
    ):
        periodic_project_checks(
            prim=prim,
            max_length=[0.0, 0.0, 8.01, 6.01, 4.01],
            occ_site_basis_functions_specs=[
                {
                    "sublat_indices": [0],
                    "composition": {
                        "mol.x": 0.3,
                        "mol.y": 0.4,
                        "mol.z": 0.3,
                    },
                }
            ],
        )


def test_FCC_binary_Hstrain_disp_prim():
    name = "FCC_binary_Hstrain_disp_prim.json"
    prim = casmconfig.Prim.from_dict(data=read_required(prim_dir / name))
    periodic_project_checks(
        prim=prim,
        max_length=[0.0, 0.0, 4.01, 2.9, 2.9],
        occ_site_basis_functions_specs="chebychev",
    )
