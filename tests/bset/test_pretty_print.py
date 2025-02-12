import io

import libcasm.configuration as casmconfig
from casm.project.bset._print_bset import (
    pretty_print_functions_by_orbit,
    pretty_print_occ_site_functions,
)
from casm.project.json_io import read_required


def test_site_functions(shared_datadir):
    prim = casmconfig.Prim.from_dict(
        data=read_required(shared_datadir / "SiGe_prim.json"),
    )
    # basis_dict = read_required(shared_datadir / "SiGe_basis.json")
    variables = read_required(shared_datadir / "SiGe_variables.json")

    s = io.StringIO()
    pretty_print_occ_site_functions(
        variables=variables,
        prim=prim,
        out=s,
    )

    print(s.getvalue())
    assert (
        s.getvalue()
        == R"""Occupation site functions:
- \phi(\vec{r}_{n}): [value1, ...], where:
  - n: neighborhood site index
  - \vec{r}_{n}: site position
- sublattice: 0, occ_dof: [Si, Ge]
  - \phi(\vec{r}_{n}) = [-1, 1]
- sublattice: 1, occ_dof: [Si, Ge]
  - \phi(\vec{r}_{n}) = [-1, 1]
"""
    )


def test_functions(shared_datadir):
    prim = casmconfig.Prim.from_dict(
        data=read_required(shared_datadir / "SiGe_prim.json"),
    )
    basis_dict = read_required(shared_datadir / "SiGe_basis.json")
    variables = read_required(shared_datadir / "SiGe_variables.json")

    s = io.StringIO()
    pretty_print_functions_by_orbit(
        basis_dict=basis_dict,
        variables=variables,
        prim=prim,
        out=s,
    )

    assert "\\Phi_{43}" in s.getvalue()
