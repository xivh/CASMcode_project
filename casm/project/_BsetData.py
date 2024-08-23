import pathlib
from typing import Optional, Union
import re

from casm.bset import build_cluster_functions, make_clex_basis_specs, write_clexulator
from casm.bset.cluster_functions import ClexBasisSpecs, ClusterFunctionsBuilder
from casm.project._Project import Project
from casm.project.json_io import printpathstr, read_optional, safe_dump
from libcasm.clexulator import (
    Clexulator,
    ClusterExpansion,
    Correlations,
    LocalClexulator,
    LocalCorrelations,
    LocalClusterExpansion,
    make_clexulator,
    make_local_clexulator,
)
from libcasm.configuration import (
    Configuration,
    ConfigurationWithProperties,
)
from libcasm.clusterography import Cluster, ClusterOrbitGenerator
from libcasm.occ_events import OccEvent


class BsetData:
    """Manage basis set data for a CASM project

    .. code-block:: shell

        <project>/
        └── basis_sets/
            └── bset.<id>/
                ├── bspecs.json
                ├── meta.json
                ├── basis.json
                ├── equivalents_info.json
                ├── variables.json
                ├── generated_files.json
                ├── <projectname>_Clexulator_<id>.json
                ├── 0/
                │   ├── <projectname>_Clexulator_<id>_0.cpp
                │   └── variables.json
                ├── 1/
                │   └── <projectname>_Clexulator_<id>_1.cpp
                │   └── variables.json
                ...

    Input files summary:

    - `bspecs.json`: Basis set specifications, used to construct
      :class:`~casm.bset.cluster_functions.ClexBasisSpecs` which specifies how to
      generate clusters and cluster functions.
    - `meta.json`: Metadata for the basis set. JSON formatted file with custom metadata
      for any use case. If `desc` exists, it will be printed as a descriptive summary
      by ``print``.

    Generated files summary:

    - `basis.json`: A description of the generated cluster expansion basis set. See the
      CASM documentation for the `basis.json file format
      <https://prisms-center.github.io/CASMcode_docs/formats/casm/clex/ClexBasis/>`_.
    - `equivalents_info.json`: The equivalents info provides the phenomenal cluster and
      local-cluster orbits for all symmetrically equivalent local-cluster expansions, and
      the indices of the factor group operations used to construct each equivalent
      local cluster expansion from the prototype local-cluster expansion.
    - `<Project>_Clexulator_<id>.cpp`: The Clexulator source file, or a prototype local
      Clexulator source file.
    - `variables.json`: A file for each Clexulator (including local Clexulator) which
      contains the variables used by the jinja2 templates as well as information like
      basis function formulas generated during the write process. Values in this file
      correspond to documented attributes of the following classes:
      - For version `v1.basic`: :class:`~casm.bset.clexwriter.WriterV1Basic`
      - For version `v1.diff`: :class:`~casm.bset.clexwriter.WriterV1Diff` (TODO)
    - `<Project>_Clexulator_<id>.o`: The compiled Clexulator object file.
    - `<Project>_Clexulator_<id>.so`: The compiled Clexulator shared object library
      file.
    - `<equivalent_index>/<Project>_Clexulator_<id>_<equivalent_index>.cpp`: The
      Clexulator source file for one of the equivalent local basis sets.

    - `generated_files.json`: A list of generated files, used to track generated files
      and clean up old files.

    Command summary:

    - :func:`~casm.bset.BsetData.load`: Load current data
      - Read bspecs.json, meta.json, basis.json, equivalents_info.json, and
        generated_files.json (if they exist)

    - :func:`~casm.bset.BsetData.set_bspecs` and
      :func:`~casm.bset.BsetData.make_bspecs`: Set or make basis set specifications
      (bspecs.json)
      - Clear existing bspecs.json file and generated data (if force=True)
      - Write bspecs.json and meta.json
      - Does not write or compile a Clexulator

    - :func:`~casm.bset.BsetData.update`: Write and compile the Clexulator or
      LocalClexulator
      - Clear existing generated files (if force=True)
      - Write the Clexulator or LocalClexulator source file(s) (if compile_only=False)
      - Compile the Clexulator or LocalClexulator (if no_compile=False)

    - :func:`~casm.bset.BsetData.commit`: Write current data
      - Writes meta.json

    Attributes summary:

    """

    def __init__(self, proj: Project, id: str, meta: Optional[dict] = None):

        if not re.match(
            R"^\w+",
            id,
        ):
            raise Exception(
                f"id='{id}' is not a valid basis set name: ",
                "Must consist alphanumeric characters and underscores only.",
            )

        self.proj = proj
        """Project: CASM project"""

        self.id = id
        """str: Basis set identifier"""

        if meta is None:
            meta = dict()
        self.meta = meta
        """dict: A description of the enumeration, saved as `meta.json`."""

        self.bset_dir = self.proj.dir.bset_dir(bset=id)
        """pathlib.Path: Basis set directory"""

        self.clex_basis_specs = None
        """ClexBasisSpecs: Clexulator basis set specifications"""

        self.version = None
        """str: Version of the Clexulator to write"""

        self.linear_function_indices = None
        """Optional[set[int]]: Linear function indices to include in the Clexulator"""

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

        self.generated_files = None
        """Optional[dict]: Information on generated files.
        
        Format:
    
        - `all`: dict, All generated files, relative to the bset_dir
        - `src_path`: str, Clexulator or prototype local clexulator source file path,
          relative to the bset_dir
        - `local_src_path: list[str], Local Clexulator source file paths, relative to
          the bset_dir  
        
        """

        self.src_path = None

        self.local_src_path = None
        """list[pathlib.Path]: Local Clexulator source file paths"""

        self._variables = None
        self._local_variables = None

        self.load()

    def load(self):
        """Read basis set data from files in the basis set directory.

        This will replace the current contents of this BsetData object with the
        contents of the associated files, or set the current contents to None if the
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
            self.linear_function_indices = data.get("linear_function_indices", None)
            self.version = data.get("version", "v1.basic")

        else:
            self.clex_basis_specs = None
            self.linear_function_indices = None
            self.version = None

    def basis_dict(self) -> Optional[dict]:
        return read_optional(self.bset_dir / "basis.json")

    def equivalents_info(self) -> Optional[dict]:
        return read_optional(self.bset_dir / "equivalents_info.json")

    def generated_files(self) -> Optional[dict]:
        path = self.bset_dir / "equivalents_info.json"
        return read_optional(path)

    def src_path(self) -> Optional[pathlib.Path]:
        """Returns Clexulator or prototype local clexulator source file path

        Returns
        -------
        Optional[pathlib.Path]
            Clexulator or prototype local clexulator source file path, as read
            from generated_files.json; otherwise None.
        """
        gen = self.generated_files()
        if gen is None:
            return None
        _src_path = gen.get("src_path")
        if _src_path is None:
            return None
        return self.bset_dir / _src_path

    def local_src_path(self) -> Optional[list[pathlib.Path]]:
        """Returns list of LocalClexulator source file paths

        Returns
        -------
        Optional[list[pathlib.Path]]
            List of LocalClexulator source file paths, as read
            from generated_files.json; otherwise None.
        """
        gen = self.generated_files()
        if gen is None:
            return None
        _local_src_path = gen.get("local_src_path")
        if _local_src_path is None:
            return None
        return [self.bset_dir / p for p in _local_src_path]

    def variables(self, i_equiv: Optional[int] = None) -> Optional[dict]:
        """Returns variables dict

        A file for each Clexulator (including local Clexulator) which
        contains the variables used by the jinja2 templates as well as information like
        basis function formulas generated during the write process. Values in this file
        correspond to documented attributes of the following classes:

        - For version `v1.basic`: :class:`~casm.bset.clexwriter.WriterV1Basic`
        - For version `v1.diff`: :class:`~casm.bset.clexwriter.WriterV1Diff` (TODO)

        Parameters
        ----------
        i_equiv: Optional[int] = None
            The equivalent index. If None, the variables.json file in the basis set
            directory is read; otherwise, the variables.json file in the `i_equiv`-th
            equivalent local basis set directory is read.

        Returns
        -------
        Optional[dict]
            Contents of variables.json, or None if the file does not exist.
        """
        if i_equiv is None:
            return read_optional(self.bset_dir / "variables.json")
        else:
            # read variables.json if it exists
            path = self.bset_dir / str(i_equiv) / "variables.json"
            return read_optional(path)

    def clean(self, verbose: bool = True):
        """Remove all generated files associated with the basis set, as read from
        generated_files.json"""
        # read generated_files.json if it exists
        generated_files = self.generated_files()

        if generated_files is None:
            if verbose:
                print("No generated files to remove")
            return

        files = generated_files.get("all", [])
        for file in files:
            path = self.bset_dir / file
            if path.exists():
                if verbose:
                    print(f"Removing {printpathstr(path)}")
                path.unlink()

    def commit(self, verbose: bool = True):
        """Write the basis set meta data

        This will erase the associated file if `self.meta` is None.
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

        # # write bspecs.json
        # path = self.proj.dir.bspecs(bset=self.id)
        # if self.clex_basis_specs is not None:
        #     data = self.clex_basis_specs.to_dict()
        #
        #     # additional data
        #     if self.linear_function_indices is not None:
        #         data["linear_function_indices"] = self.linear_function_indices
        #     if self.version is not None:
        #         data["version"] = self.version
        #     if self.src_path is not None:
        #         data["src_path"] = str(self.src_path)
        #     if self.local_src_path is not None:
        #         data["local_src_path"] = [str(p) for p in self.local_src_path]
        #
        #     safe_dump(data=data, path=path, quiet=quiet, force=True)
        # elif path.exists():
        #     path.unlink()
        #
        # # write basis.json
        # path = self.proj.dir.basis(bset=self.id)
        # if self.basis_dict is not None:
        #     safe_dump(data=self.basis_dict, path=path, quiet=quiet, force=True)
        # elif path.exists():
        #     path.unlink()
        #
        # # write equivalents_info.json
        # path = self.bset_dir / "equivalents_info.json"
        # if self.equivalents_info is not None:
        #     safe_dump(data=self.equivalents_info, path=path, quiet=quiet, force=True)
        # elif path.exists():
        #     path.unlink()

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

    def build(
        self,
        make_equivalents: bool = True,
        make_all_local_basis_sets: bool = True,
        verbose: bool = False,
    ) -> ClusterFunctionsBuilder:
        """Construct the cluster functions for the basis set, but do not write anything

        This uses the current basis set specifications to construct clusters and
        cluster functions. It raises if no basis set specifications exist.


        Parameters
        ----------
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
                "Error in BsetData.make_cluster_functions: "
                "no basis set specifications found"
            )
        if self.proj.prim_neighbor_list is None:
            raise Exception(
                "Error in BsetData.make_cluster_functions: "
                "project prim_neighbor_list is None"
            )
        return build_cluster_functions(
            prim=self.proj.prim,
            clex_basis_specs=self.clex_basis_specs,
            prim_neighbor_list=self.proj.prim_neighbor_list,
            make_equivalents=make_equivalents,
            make_all_local_basis_sets=make_all_local_basis_sets,
            verbose=verbose,
        )

    def update(
        self,
        no_compile: bool = False,
        only_compile: bool = False,
    ):
        """Write the Clexulator source file(s) for the basis set

        Parameters
        ----------
        no_compile: bool = False
            If True, do not compile the Clexulator or LocalClexulator.

        only_compile: bool = False
            If True, only compile the Clexulator or LocalClexulator from existing
            source files, do not write the source file(s).

        """
        if self.proj.prim_neighbor_list is None:
            raise Exception(
                "Error in BsetData.write_clexulator: "
                "project prim_neighbor_list is None"
            )

        self.load()
        if self.clex_basis_specs is None:
            raise Exception(
                "Error in BsetData.write_clexulator: "
                "no basis set specifications found"
            )

        if only_compile is False:
            write_clexulator(
                prim=self.proj.prim,
                clex_basis_specs=self.clex_basis_specs,
                bset_dir=self.bset_dir,
                prim_neighbor_list=self.proj.prim_neighbor_list,
                project_name=self.proj.name,
                bset_name=self.id,
                version=self.version,
                linear_function_indices=self.linear_function_indices,
                cpp_fmt=None,
            )

        if no_compile:
            return

        src_path = self.src_path()
        if src_path is None:
            raise ValueError("Error in BsetData.update: No Clexulator src_path.")

        make_clexulator(
            source=str(src_path),
            prim_neighbor_list=self.proj.prim_neighbor_list,
        )

        if self.local_src_path() is not None:
            make_local_clexulator(
                source=str(src_path),
                prim_neighbor_list=self.proj.prim_neighbor_list,
            )

    def clexulator(self) -> Optional[Clexulator]:
        """Optional[Clexulator]: The Clexulator for the basis set, available if
        :attr:`BsetData.clex_basis_specs` is not None.

        When accessed, the Clexulator will be written if it has not yet been written,
        and compiled if it has not yet been compiled.
        """
        src_path = self.src_path()
        if src_path is None:
            return None

        return make_clexulator(
            source=str(src_path),
            prim_neighbor_list=self.proj.prim_neighbor_list,
        )

    def local_clexulator(self) -> Optional[LocalClexulator]:
        """Optional[LocalClexulator]: The LocalClexulator for the basis set, if
        available.

        When accessed, the LocalClexulator will be written if it has not yet been
        written, and compiled if it has not yet been compiled.
        """
        src_path = self.src_path()
        if src_path is None:
            return None
        local_src_path = self.local_src_path()
        if local_src_path is None:
            return None
        return make_local_clexulator(
            source=str(src_path),
            prim_neighbor_list=self.proj.prim_neighbor_list,
        )
