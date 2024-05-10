import numpy as np
from typing import Optional
from casm.project._Project import Project
from casm.project.json_io import (
    read_required,
    safe_dump,
)


class EnumCommand:
    """Methods to enumerate supercells, configurations, events, etc."""

    def __init__(self, proj: Project):
        self.proj = proj

    def supercells_by_volume(
        self,
        max: int,
        min: int = 1,
        unit_cell: Optional[np.ndarray] = None,
        dirs: str = "abc",
        diagonal_only: bool = False,
        fixed_shape: bool = False,
        id: Optional[str] = None,
    ):
        """Enumerate supercells by volume (multiples of the primitive cell volume)

        Parameters
        ----------
        max : int
            The maximum volume superlattice to enumerate. The volume is measured
            relative the unit cell being used to generate supercells.
        min : int, default=1
            The minimum volume superlattice to enumerate. The volume is measured
            relative the unit cell being used to generate supercells.
        dirs : str, default="abc"
            A string indicating which lattice vectors to enumerate over. Some
            combination of 'a', 'b', and 'c', where 'a' indicates the first lattice
            vector of the unit cell, 'b' the second, and 'c' the third.
        unit_cell: Optional[np.ndarray] = None,
            An integer shape=(3,3) transformation matrix `U` allows specifying an
            alternative unit cell that can be used to generate superlattices of the
            form `S = (L @ U) @ T`. If None, `U` is set to the identity matrix.
        diagonal_only: bool = False
            If true, restrict :math:`T` to diagonal matrices.
        fixed_shape: bool = False
            If true, restrict :math:`T` to diagonal matrices with diagonal coefficients
            :math:`[m, 1, 1]` (1d), :math:`[m, m, 1]` (2d), or :math:`[m, m, m]` (3d),
            where the dimension is determined from `len(dirs)`.
        id: Optional[str] = None
            An optional enumeration identifier string specifying where results are
            stored. Data related to the enumeration is stored in the CASM project at
            `<project>/enumerations/enum.<id>/`. If None, a sequential id is
            generated automatically.

        Returns
        -------
        id: str
            An enumeration id specifying where results are stored.
        """
        return None

    def occ_by_supercell(
        self,
    ):
        # read supercell set
        # configuration set

        # run enumeration

        # save results in <project>/enumerations/enum.<id>

        # option to merge into master config list

        print("occ_by_supercell")
        return None

    def occ_by_supercell_list(
        self,
    ):
        print("occ_by_supercell_list")
        return None

    def occ_by_cluster(
        self,
    ):
        print("occ_by_cluster")
        return None

    def strain_by_grid_coordinates(
        self,
    ):
        print("strain_by_grid_coordinates")
        return None

    def strain_by_grid_range(
        self,
    ):
        print("strain_by_grid_range")
        return None

    def strain_by_irreducible_wedge(
        self,
    ):
        print("strain_by_irreducible_wedge")
        return None

    def disp_by_grid_coordinates(
        self,
    ):
        print("disp_by_grid_coordinates")
        return None

    def magpsin_by_X(
        self,
    ):
        print("magspin_by_X")
        return None
