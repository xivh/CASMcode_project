import pathlib
from typing import Optional, Union

from casm.bset import build_cluster_functions, make_clex_basis_specs, write_clexulator
from casm.bset.cluster_functions import ClexBasisSpecs, ClusterFunctionsBuilder
from casm.project._ClexDescription import ClexDescription
from casm.project._Project import Project
from casm.project.json_io import read_optional, safe_dump
from libcasm.clexulator import (
    Clexulator,
    LocalClexulator,
    PrimNeighborList,
    make_clexulator,
    make_local_clexulator,
)
from libcasm.clusterography import Cluster, ClusterOrbitGenerator
from libcasm.occ_events import OccEvent


class BsetData:
    def __init__(self, proj: Project, id: str, meta: Optional[dict] = None):
        self.proj = proj
        """Project: CASM project"""

        self.id = id
        """str: Enumeration identifier"""

        if meta is None:
            meta = dict()
        self.meta = meta
        """dict: A description of the enumeration, saved as `meta.json`."""

        self.bset_dir = self.proj.dir.bset_dir(id)
        """pathlib.Path: Basis set directory"""

        self.clex_basis_specs = None
        """ClexBasisSpecs: Clexulator basis set specifications"""

        self.version = None
        """str: Version of the Clexulator to write"""

        self.linear_function_indices = None
        """Optional[set[int]]: Linear function indices to include in the Clexulator"""

        self.src_path = None
        """pathlib.Path: Clexulator or prototype local clexulator source file path"""

        self.local_src_path = None
        """list[pathlib.Path]: Local Clexulator source file paths"""

        self.prim_neighbor_list = None
        """PrimNeighborList: Prim neighbor list"""

        self.basis_dict = None
        """dict: A description of a cluster expansion basis set.
        
        See the CASM documentation for the
        `basis.json format <https://prisms-center.github.io/CASMcode_docs/formats/casm/clex/ClexBasis/>`_.
        """

        self.equivalents_info = None
        """dict: The equivalents info provides the phenomenal cluster and local-cluster
        orbits for all symmetrically equivalent local-cluster expansions, and the
        indices of the factor group operations used to construct each equivalent
        local cluster expansion from the prototype local-cluster expansion. 
            
        When there is an orientation to the local-cluster expansion this information
        allows generating the proper diffusion events, etc. from the prototype.
        
        See the CASM documentation for the
        `equivalents_info.json format <TODO>`_.
        """

        self._clexulator = None  # hold Clexulator
        self._local_clexulator = None  # hold LocalClexulator

        self.load()

    def load(self):
        """Read basis set data from files in the basis set directory.

        This will replace the current contents of this BsetData object with the
        contents of the associated files, or delete the current contents if the
        associated files do not exist.
        """

        # read meta.json if it exists
        path = self.bset_dir / "meta.json"
        self.meta = read_optional(path, default=dict())

        # read bspecs.json if it exists
        path = self.proj.dir.bspecs(bset=self.id)
        data = read_optional(path, default=None)
        if data is not None:
            self.clex_basis_specs = ClexBasisSpecs.from_dict(
                data=data,
                prim=self.proj.prim,
            )

            # additional data
            self.linear_function_indices = data.get("linear_function_indices", None)
            self.version = data.get("version", "v1.basic")
            self.src_path = data.get("src_path", None)
            if self.src_path is not None:
                self.src_path = pathlib.Path(self.src_path)
            self.local_src_path = data.get("local_src_path", None)
            if self.local_src_path is not None:
                self.local_src_path = [pathlib.Path(p) for p in self.local_src_path]

        else:
            self.clex_basis_specs = None

        # read basis.json if it exists
        path = self.proj.dir.basis(bset=self.id)
        self.basis_dict = read_optional(path, default=None)

        # read equivalents_info.json if it exists
        path = self.bset_dir / "equivalents_info.json"
        self.equivalents_info = read_optional(path, default=None)

    def commit(self, verbose: bool = True):
        """Write the basis set data to files in the basis set directory

        If the data does not exist in this object, this will erase the associated
        files if they do exist.
        """

        quiet = not verbose
        self.bset_dir.mkdir(parents=True, exist_ok=True)

        # write meta.json:
        path = self.bset_dir / "meta.json"
        if len(self.meta) > 0:
            if not isinstance(self.meta, dict):
                raise TypeError(
                    "Error in BsetData.commit: BsetData.meta must be a dict"
                )
            safe_dump(
                data=self.meta,
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

        # write bspecs.json
        path = self.proj.dir.bspecs(bset=self.id)
        if self.clex_basis_specs is not None:
            data = self.clex_basis_specs.to_dict()

            # additional data
            if self.linear_function_indices is not None:
                data["linear_function_indices"] = self.linear_function_indices
            if self.version is not None:
                data["version"] = self.version
            if self.src_path is not None:
                data["src_path"] = str(self.src_path)
            if self.local_src_path is not None:
                data["local_src_path"] = [str(p) for p in self.local_src_path]

            safe_dump(data=data, path=path, quiet=quiet, force=True)
        elif path.exists():
            path.unlink()

        # write basis.json
        path = self.proj.dir.basis(bset=self.id)
        if self.basis_dict is not None:
            safe_dump(data=self.basis_dict, path=path, quiet=quiet, force=True)
        elif path.exists():
            path.unlink()

        # write equivalents_info.json
        path = self.bset_dir / "equivalents_info.json"
        if self.equivalents_info is not None:
            safe_dump(data=self.equivalents_info, path=path, quiet=quiet, force=True)
        elif path.exists():
            path.unlink()

    def reset(self):
        """Reset the basis set data to an empty state

        Does not delete any files. Does not change the id, meta, or bset_dir.
        """
        self.clex_basis_specs = None
        self.version = None
        self.linear_function_indices = None
        self.src_path = None
        self.local_src_path = None
        self.basis_dict = None
        self.equivalents_info = None
        self._clexulator = None
        self._local_clexulator = None

    def set_clex_basis_specs(
        self,
        clex_basis_specs: ClexBasisSpecs,
        version: str = "v1.basic",
        linear_function_indices: Optional[set[int]] = None,
    ):
        """Reset the basis set data and set the ClexBasisSpecs

        Does not delete any files. Does not change the id, meta, or bset_dir.

        Parameters
        ----------
        clex_basis_specs : ClexBasisSpecs
            The ClexBasisSpecs object
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

        """
        self.reset()

        self.clex_basis_specs = clex_basis_specs
        self.version = version
        self.linear_function_indices = linear_function_indices

    def make_clex_basis_specs(
        self,
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
    ):
        """Reset the basis set data and set the ClexBasisSpecs

        Does not delete any files. Does not change the id, meta, or bset_dir.

        Parameters
        ----------
        prim: Union[libcasm.xtal.Prim, libcasm.configuration.Prim, dict, str, \
        pathlib.Path]
            The prim, with symmetry information. May be provided as a Prim instance, a
            Prim dict, or the path to a file containing the Prim dict.

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

        """
        self.reset()

        self.clex_basis_specs = make_clex_basis_specs(
            prim=self.proj.prim,
            dofs=dofs,
            max_length=max_length,
            custom_generators=custom_generators,
            phenomenal=phenomenal,
            cutoff_radius=cutoff_radius,
            occ_site_basis_functions_specs=occ_site_basis_functions_specs,
            global_max_poly_order=global_max_poly_order,
            orbit_branch_max_poly_order=orbit_branch_max_poly_order,
        )
        self.version = version
        self.linear_function_indices = linear_function_indices

    def make_cluster_functions(
        self,
        prim_neighbor_list: Optional[PrimNeighborList] = None,
        make_equivalents: bool = True,
        make_all_local_basis_sets: bool = True,
        verbose: bool = False,
    ) -> ClusterFunctionsBuilder:
        """Construct the cluster functions for the basis set

        This uses the current basis set specifications to construct clusters and
        cluster functions. It raises if no basis set specifications exist.


        Parameters
        ----------
        prim_neighbor_list: Optional[libcasm.clexulator.PrimNeighborList] = None
            The :class:`PrimNeighborList` is used to uniquely index sites with local
            variables included in the cluster functions, relative to a reference unit
            cell. If not provided, a PrimNeighborList is constructed using default
            parameters that include all sites with degrees of freedom (DoF) and the
            default shape used by CASM projects.

            In most cases, the default should be used. If multiple clexulator are being
            used with a single supercell neighbor list, then the same
            prim_neighbor_list should be used for all clexulators.

        make_equivalents: bool = True
            If True, make all equivalent clusters and functions. Otherwise, only
            construct and return the prototype clusters and functions on the prototype
            cluster (i.e. ``i_equiv=0`` only).

        make_all_local_basis_sets: bool = True
            If True, make local clusters and functions for all phenomenal
            clusters in the primitive cell equivalent by prim factor group symmetry.
            Requires that `make_equivalents` is True.

        verbose: bool = False
            Print progress statements

        Returns
        -------
        builder: casm.bset.cluster_functions.ClusterFunctionsBuilder
            The ClusterFunctionsBuilder data structure holds the generated cluster
            functions and associated clusters.

        """
        if self.clex_basis_specs is None:
            raise Exception(
                "Error in BsetData.build: no basis set specifications found"
            )
        if prim_neighbor_list is not None:
            self.prim_neighbor_list = prim_neighbor_list

        return build_cluster_functions(
            prim=self.proj.prim,
            clex_basis_specs=self.clex_basis_specs,
            prim_neighbor_list=self.prim_neighbor_list,
            make_equivalents=make_equivalents,
            make_all_local_basis_sets=make_all_local_basis_sets,
            verbose=verbose,
        )

    def write_clexulator(
        self,
        prim_neighbor_list: Optional[PrimNeighborList] = None,
    ):
        """Write the Clexulator source file(s) for the basis set

        Parameters
        ----------
        prim_neighbor_list: Optional[PrimNeighborList] = None
            The :class:`PrimNeighborList` is used to uniquely index sites with local
            variables included in the cluster functions, relative to a reference unit
            cell. If not provided, a PrimNeighborList is constructed using default
            parameters that include all sites with degrees of freedom (DoF) and the
            default shape used by CASM projects.

            In most cases, the default should be used. If multiple clexulator are being
            used with a single supercell neighbor list, then the same
            prim_neighbor_list should be used for all clexulators.

        """
        if prim_neighbor_list is not None:
            self.prim_neighbor_list = prim_neighbor_list

        self.src_path, self.local_src_path, self.prim_neighbor_list = write_clexulator(
            prim=self.proj.prim,
            clex_basis_specs=self.clex_basis_specs,
            bset_dir=self.bset_dir,
            prim_neighbor_list=self.prim_neighbor_list,
            project_name=self.proj.name,
            bset_name=self.id,
            version=self.version,
            linear_function_indices=self.linear_function_indices,
            cpp_fmt=None,
        )

    @property
    def clexulator(self) -> Optional[Clexulator]:
        """Optional[Clexulator]: The Clexulator for the basis set, if available."""
        if self.src_path is None:
            return None
        if self._clexulator is None:
            self._clexulator = make_clexulator(
                source=str(self.src_path),
                prim_neighbor_list=self.prim_neighbor_list,
            )
        return self._clexulator

    @property
    def local_clexulator(self) -> Optional[LocalClexulator]:
        """Optional[LocalClexulator]: The LocalClexulator for the basis set, if
        available."""
        if self.local_src_path is None:
            return None
        if self._local_clexulator is None:
            self._local_clexulator = make_local_clexulator(
                source=str(self.src_path),
                prim_neighbor_list=self.prim_neighbor_list,
            )
        return self._local_clexulator


class BsetCommand:
    """Methods to construct and print cluster expansion basis sets"""

    def __init__(self, proj: Project):
        self.proj = proj

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

    def list(self):
        """Print all basis sets"""
        for id in self.all():
            basis_set = self.get(id)
            print(basis_set)

    def get(self, id: str):
        """Load basis set data

        Parameters
        ----------
        id : str
            The enumeration identifier

        Returns
        -------
        bset: BsetData
            The enumeration data
        """
        return BsetData(proj=self.proj, id=id)

    def make_bspecs_template(
        self,
        name: str = None,
    ):
        """Create a bspecs.json template file"""
        return None

    def update(
        self,
        bset: Optional[str] = None,
        clex: Optional[ClexDescription] = None,
        bspecs_data: Optional[dict] = None,
        no_compile: bool = False,
        only_compile: bool = False,
    ):
        """Write and compile the Clexulator source file for a basis set

        Parameters
        ----------
        bset: Optional[str] = None
            Specify the basis set by bset name.
        clex: Optional[ClexDescription] = None
            Specify the basis set by ClexDescription.
        bspecs_data: Optional[dict] = None
            Use provided `bspecs_data` and write to `bspecs.json` instead of reading
            `bspecs.json`. Will overwrite any existing `bspecs.json` file.
        no_compile: bool = False
            If `no_compile` is True, then the Clexulator source file is written but
            not compiled. By default the Clexulator source file is immediately compiled.
        only_compile: bool = False
            If `only_compile` is True, keep the existing Clexulator source file but
            re-compile it. By default the Clexulator source file is written and then
            compiled.
        """
        print("update")
        # bset = self._check_bset(clex=clex, bset=bset)
        #
        # bspecs_path = self.proj.dir.bspecs(clex=clex, bset=bset)
        # if bspecs_data is None:
        #     bspecs_data = read_required(bspecs_path)
        # else:
        #     safe_dump(data=bspecs_data, path=bspecs_path, force=True)
        return None

    def orbit_prototypes(
        self,
        name: str = None,
    ):
        return None

    def clusters(self):
        return None

    def functions(self):
        return None
