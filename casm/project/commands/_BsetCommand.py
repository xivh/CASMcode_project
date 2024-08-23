from typing import Optional, TextIO, Union
import sys

from casm.bset.cluster_functions import ClexBasisSpecs, ClusterFunctionsBuilder
from casm.project._Project import Project
from casm.project import BsetData
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

    def set_bspecs(
        self,
        id: str,
        clex_basis_specs: ClexBasisSpecs,
        version: str = "v1.basic",
        linear_function_indices: Optional[set[int]] = None,
        force: bool = False,
    ):
        """Set basis set specs for a basis set

        Notes
        -----
        - This will create a new basis set with given id if it does not exist
        - This will overwrite an existing basis set specs if it does exist, and
          force is True

        Parameters
        ----------
        id : str
            The basis set identifier. Must consist alphanumeric characters and
            underscores only.
        clex_basis_specs : ClexBasisSpecs
            The basis set specifications
        force : bool = False
            If True, overwrite existing basis set specs; otherwise raise if basis
            set specs already exist.

        """
        bset = self.get(id)
        self.last = bset
        if bset.clex_basis_specs is not None and force is False:
            raise Exception(
                f"Basis set specs already exist for {id}. Use force=True to overwrite."
            )
        bset.set_clex_basis_specs(
            clex_basis_specs=clex_basis_specs,
            version=version,
            linear_function_indices=linear_function_indices,
        )
        bset.commit()

    def make_bspecs(
        self,
        id: str,
        dofs: Optional[list[str]] = None,
        max_length: Optional[list[float]] = [],
        custom_generators: Optional[list[ClusterOrbitGenerator]] = [],
        phenomenal: Union[Cluster, OccEvent, None] = None,
        cutoff_radius: Optional[list[float]] = [],
        occ_site_basis_functions_specs: Union[str, list[dict], None] = None,
        global_max_poly_order: Optional[int] = None,
        orbit_branch_max_poly_order: Optional[dict] = None,
        version: str = "v1.basic",
        linear_function_indices: Optional[set[int]] = None,
        force: bool = False,
    ):
        """Set basis set specs for a basis set

        Notes
        -----
        - This will create a new basis set with given id if it does not exist
        - This will overwrite an existing basis set specs if it does exist, and
          force is True

        Parameters
        ----------
        id : str
            The basis set identifier. Must consist alphanumeric characters and
            underscores only.
        dofs: Optional[list[str]] = None
            An list of string of dof type names that should be used to construct basis
            functions. The default value is all DoF types included in the prim.

        max_length: list[float] = []
            The maximum site-to-site distance to allow in clusters, by number of sites
            in the cluster. Example: `[0.0, 0.0, 5.0, 4.0]` specifies that pair
            clusters up to distance 5.0 and triplet clusters up to distance 4.0 should
            be included. The null cluster and point cluster values (elements 0 and 1)
            are arbitrary.

        custom_generators: list[libcasm.clusterography.ClusterOrbitGenerator] = []]
            Specifies clusters that should be uses to construct orbits regardless of the
            `max_length` or `cutoff_radius` parameters.

        phenomenal: Union[libcasm.clusterography.Cluster, libcasm.occ_events.OccEvent, \
        None] = None
            If provided, generate local cluster functions using the invariant group of
            the phenomenal cluster or event. By default, periodic cluster functions are
            generated.

        cutoff_radius: list[float] = []
            For local clusters, the maximum distance of sites from any phenomenal
            cluster site to include in the local environment, by number of sites in the
            cluster. The null cluster value (element 0) is arbitrary.

        occ_site_basis_functions_specs: Union[str, list[dict], None] = None
            Provides instructions for constructing occupation site basis functions.
            The accepted options are "chebychev", "occupation", or a `list[dict]`
            a specifying sublattice-specific choice of site basis functions. This
            parameter corresponds to the value of

            .. code-block:: Python

                "dof_specs": {
                    "occ": {
                        "site_basis_functions": ...
                    }
                }

            as described in detail in the section
            :ref:`DoF Specifications <sec-dof-specifications>` and is required for
            functions of occupation DoF.

        global_max_poly_order: Optional[int] = None
            The maximum order of polynomials of continuous DoF to generate, for any
            orbit not specified more specifically by `orbit_branch_max_poly_order`.

        orbit_branch_max_poly_order: Optional[dict[int, int]] = None
            Specifies for continuous DoF the maximum polynomial order to generate by
            cluster size, according to
            ``orbit_branch_max_poly_order[cluster_size] = max_poly_order``. By default,
            for a given cluster orbit, polynomials of order up to the cluster size are
            created. Higher order polynomials are requested either according to cluster
            size using `orbit_branch_max_poly_order` or globally using
            `global_max_poly_order`. The most specific level specified is used.

        version: str = "v1.basic"
            The Clexulator version to write. One of:

            - "v1.basic": Standard CASM v1 compatible Clexulator, without automatic
              differentiation
            - "v1.diff": (TODO) CASM v1 compatible Clexulator, with ``fadbad`` automatic
              differentiation enabled

        linear_function_indices: Optional[set[int]] = None
            (Experimental feature) The linear indices of the functions that will be
            included. If None, all functions will be included in the Clexulator.
            Otherwise, only the specified functions will be included in the Clexulator.
            Generally this is not known the first time a Clexulator is generated, but
            after fitting coefficients it may be used to re-generate the Clexulator
            with the subset of the basis functions needed.
        force : bool = False
            If True, overwrite existing basis set specs; otherwise raise if basis
            set specs already exist.
        """
        bset = self.get(id)
        self.last = bset
        if bset.clex_basis_specs is not None and force is False:
            raise Exception(
                f"Basis set specs already exist for {id}. Use force=True to overwrite."
            )
        bset.make_clex_basis_specs(
            dofs=dofs,
            max_length=max_length,
            custom_generators=custom_generators,
            phenomenal=phenomenal,
            cutoff_radius=cutoff_radius,
            occ_site_basis_functions_specs=occ_site_basis_functions_specs,
            global_max_poly_order=global_max_poly_order,
            orbit_branch_max_poly_order=orbit_branch_max_poly_order,
            version=version,
            linear_function_indices=linear_function_indices,
        )
        bset.commit()

    def update(
        self,
        id: str,
        no_compile: bool = False,
        only_compile: bool = False,
    ):
        """Write and compile the Clexulator source file for a basis set
        with existing basis set specs.

        Parameters
        ----------
        id : str
            The basis set identifier. Must consist alphanumeric characters and
            underscores only.
        no_compile: bool = False
            If `no_compile` is True, then the Clexulator source file is written but
            not compiled. By default the Clexulator source file is immediately compiled.
        only_compile: bool = False
            If `only_compile` is True, keep the existing Clexulator source file but
            re-compile it. By default the Clexulator source file is written and then
            compiled.
        """
        bset = self.get(id)
        self.last = bset
        if bset.clex_basis_specs is None:
            raise Exception(f"Basis set specs do not exist for {id}")
        if not only_compile:
            bset.write_clexulator()
        if not no_compile:
            _ = bset.clexulator

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
