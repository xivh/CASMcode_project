from typing import Optional, TextIO, Union
import sys

from casm.bset.cluster_functions import ClexBasisSpecs, ClusterFunctionsBuilder
from casm.project._Project import Project
from casm.project import BsetData
from casm.project.json_io import safe_dump, read_optional, read_required
from libcasm.clusterography import Cluster, ClusterOrbitGenerator
from libcasm.occ_events import OccEvent


class BsetCommand:
    """Methods to construct and print cluster expansion basis sets"""

    def __init__(self, proj: Project):
        self.proj = proj
        """Project: CASM project."""

        self.last = None
        """Optional[BsetData]: Data from the last basis set operation."""

    def _check_bset(
        self,
        bset: Optional[str] = None,
    ):
        if bset is None:
            if self.proj.settings.default_clex is None:
                raise Exception(
                    "No default clex found in project. One of bset, clex is required."
                )
            bset = self.proj.settings.default_clex.bset
        return bset

    def all(self):
        """Return the identifiers of all basis sets

        Returns
        -------
        all_bset: list[str]
            A list of basis set identifiers
        """
        return self.proj.dir.all_bset()

    def print_all(self):
        """Print all basis sets"""
        for id in self.all():
            basis_set = self.get(id)
            print(basis_set)

    def get(self, id: str):
        """Load basis set data

        Parameters
        ----------
        id : str
            The basis set identifier

        Returns
        -------
        bset: BsetData
            The enumeration data
        """
        return BsetData(proj=self.proj, id=id)

    def print_orbits(
        self,
        id: str,
        linear_orbit_indices: Optional[set[int]] = None,
        print_invariant_group: bool = False,
    ):
        bset = self.get(id)
        self.last = bset
        if bset.clex_basis_specs is None:
            raise Exception(f"Basis set {id} has not been generated yet.")

        options = PrettyPrintBasisOptions()
        options.linear_orbit_indices = linear_orbit_indices
        options.print_invariant_group = print_invariant_group

        pretty_print_orbits(
            basis_dict=bset.basis_dict,
            prim=self.proj.prim,
            options=options,
        )

    # TODO:
    # def clusters(self, ...):
    #     return None

    def print_functions(
        self,
        id: str,
        linear_orbit_indices: Optional[set[int]] = None,
        print_invariant_group: bool = False,
    ):
        bset = self.get(id)
        self.last = bset
        if bset.clex_basis_specs is None:
            raise Exception(f"Basis set {id} has not been generated yet. Use `update`.")

        options = PrettyPrintBasisOptions()
        options.linear_orbit_indices = linear_orbit_indices
        options.print_invariant_group = print_invariant_group

        pretty_print_functions(
            basis_dict=bset.basis_dict,
            prim=self.proj.prim,
            options=options,
        )

    def display_functions(
        self,
        id: str,
        linear_orbit_indices: Optional[set[int]] = None,
    ):
        """Display cluster function formulas using IPython.display

        Parameters
        ----------
        id: str
            The basis set identifier. Must consist alphanumeric characters and
            underscores only.
        linear_orbit_indices: Optional[set[int]] = None
            Linear cluster orbit indices to print associated functions for. If None,
            functions are printed for all cluster orbits.

        """
        bset = self.get(id)
        self.last = bset
        if bset.clex_basis_specs is None:
            raise Exception(f"Basis set {id} has not been generated yet. Use `update`.")

        options = PrettyPrintBasisOptions()
        options.linear_orbit_indices = linear_orbit_indices
        options.print_invariant_group = False

        display_functions(
            basis_dict=bset.basis_dict,
            prim=self.proj.prim,
            options=options,
        )
