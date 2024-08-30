import sys
from typing import TYPE_CHECKING, Optional, TextIO

import numpy as np

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal
from libcasm.sym_info import SymGroup

if TYPE_CHECKING:
    from casm.project import Project


def _print_symgroup(
    group: SymGroup,
    lattice: xtal.Lattice,
    coord: str = "frac",
    index_from: int = 0,
    out: Optional[TextIO] = None,
):
    """Print the symmetry group

    Parameters
    ----------
    group: libcasm.sym_info.SymGroup
        The symmetry group
    lattice: libcasm.xtal.Lattice
        The lattice
    coord: str = "frac"
        The coordinate mode to use for the SymOp descriptions. Options are "frac" or
        "cart".
    index_from: int = 0
        The index to start numbering the SymOps from.
    out: Optional[stream] = None
        Output stream. Defaults to `sys.stdout`.
    """
    if out is None:
        out = sys.stdout

    if coord == "frac":
        out.write(group.brief_cart(lattice=lattice, index_from=index_from))
        out.write("\n")
    elif coord == "cart":
        out.write(group.brief_frac(lattice=lattice, index_from=index_from))
        out.write("\n")
    else:
        raise ValueError("coord must be 'frac' or 'cart'")


class SymCommand:
    """Methods to analyse and print symmetry information"""

    def __init__(self, proj: "Project"):
        self.proj = proj

    def print_lattice_point_group(
        self,
        coord: str = "frac",
        index_from: int = 0,
    ):
        """Print the lattice point group"""
        lat = self.proj.prim.xtal_prim.lattice()
        _tmp_prim = casmconfig.Prim(
            xtal_prim=xtal.Prim(
                lattice=lat,
                coordinate_frac=np.zeros((3, 1)),
                occ_dof=[["X"]],
            ),
        )
        _print_symgroup(_tmp_prim.factor_group, lat, coord, index_from)

    def print_factor_group(
        self,
        coord: str = "frac",
        index_from: int = 0,
    ):
        """Print the prim factor group"""
        lat = self.proj.prim.xtal_prim.lattice()
        _print_symgroup(self.proj.prim.factor_group, lat, coord, index_from)

    def print_crystal_point_group(
        self,
        coord: str = "frac",
        index_from: int = 0,
    ):
        """Print the crystal point group"""
        lat = self.proj.prim.xtal_prim.lattice()
        _print_symgroup(self.proj.prim.crystal_point_group, lat, coord, index_from)

    def dof_space_analysis(
        self,
    ):
        print("dof_space_analysis")
        return None

    def config_space_analysis(
        self,
    ):
        print("config_space_analysis")
        return None
