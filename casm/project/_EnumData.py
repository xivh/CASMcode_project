import sys
from typing import Callable, Optional

import numpy as np

from casm.project.json_io import (
    read_optional,
    safe_dump,
)
from libcasm.configuration import (
    Configuration,
    ConfigurationSet,
    SupercellRecord,
    SupercellSet,
)
from libcasm.enumerate import (
    ConfigEnumAllOccupations,
    ScelEnum,
)

from ._ConfigEnumRunner import ConfigEnumRunner
from ._Project import Project

# EnumDataType = TypeVar("EnumDataType", bound="EnumData")


class EnumData:
    """Data structure for enumeration data in a CASM project

    The CASM project enumeration directory structure:

    .. code-block:: none

        <project>/
        └── enumerations/
            └── enum.<id>/
                ├── meta.json
                ├── scel_set.json
                ├── scel_list.json
                ├── config_set.json
                └── config_list.json

    The files in an enumeration directory are optional, and their existence depends on
    the enumeration method. If a file exists, it will be read in to the corresponding
    EnumData attribute on construction.

    An optional `meta.json` file can be used to store a description of the enumeration
    and other custom information. If "desc" is found in `meta`, it will be printed by
    `print`.

    """

    def __init__(self, proj: Project, id: str):
        """

        .. rubric:: Constructor

        The EnumData object is constructed and all enumeration data is loaded. If the
        `scel_set.json` file does not exist, an empty SupercellSet is created. Other
        enumeration data is optional. To save any changes to the enumeration data, use
        the `commit` method.

        Parameters
        ----------
        proj: Project
            The CASM project
        id: str
            The enumeration identifier. Enumeration data is stored in the enumeration
            directory at `<project>/enumerations/enum.<id>/`.
        """

        self.proj = proj
        """Project: CASM project"""

        self.id = id
        """str: Enumeration identifier"""

        enum_dir = self.proj.dir.enum_dir(id)
        self.enum_dir = enum_dir
        """pathlib.Path: Enumeration directory"""

        ### Data loaded / committed ###

        self.meta = dict()
        """dict: A description of the enumeration, saved as `meta.json`."""

        self.supercell_set = SupercellSet(prim=self.proj.prim)
        """SupercellSet: A SupercellSet, saved as `scel_set.json`.

        When `load` is called all supercells in `scel_list.json`, `scel_list.json`, 
        `config_set.json`, and `config_list.json` are loaded into `supercell_set`. 
        Supercells in a SupercellSet are unique, but are not required to be in 
        canonical form so they may be symmetrically equivalent, depending on the use 
        case.
        """

        self.supercell_list = []
        """list[Supercell]: A list of supercells, saved as `scel_list.json`."""

        self.configuration_set = ConfigurationSet()
        """ConfigurationSet: A ConfigurationSet, saved as `config_set.json`

        Configurations in a ConfigurationSet must be in the canonical supercell. 
        Configurations in a ConfigurationSet are unique, but may be 
        non-primitive, non-canonical, or symmetrically equivalent, depending on the 
        use case.
        """

        self.configuration_list = []
        """list[Configuration]: A list of configurations, saved as `config_list.json`.

        Configurations in a list do not need to be in the canonical supercell.
        """

        self.load()

    def __repr__(self):
        from libcasm.xtal import pretty_json

        s = "EnumData:\n"
        s += f"- id: {self.id}\n"

        if self.meta is not None and "desc" in self.meta:
            s += f'- desc: {pretty_json(self.meta["desc"]).strip()}\n'
        if self.supercell_set is not None and len(self.supercell_set) > 0:
            s += f"- supercell_set: {len(self.supercell_set)} supercells\n"
        if self.supercell_list is not None and len(self.supercell_list) > 0:
            s += f"- supercell_list: {len(self.supercell_list)} supercells\n"
        if self.configuration_set is not None and len(self.configuration_set) > 0:
            s += f"- configuration_set: {len(self.configuration_set)} configurations\n"
        if self.configuration_list is not None and len(self.configuration_list) > 0:
            s += (
                f"- configuration_list: {len(self.configuration_list)} configurations\n"
            )

        return s.strip()

    def load(self):
        """Read enumeration data from files in the enumeration directory.

        This will replace the current contents of this EnumData object with the
        contents of the associated files, or delete the current contents if the
        associated files do not exist.
        """

        # read meta.json if it exists
        path = self.enum_dir / "meta.json"
        self.meta = read_optional(path, default=dict())

        # read scel_set.json if it exists; else create empty
        path = self.enum_dir / "scel_set.json"
        data = read_optional(path, default=None)
        if data is not None:
            self.supercell_set = SupercellSet.from_dict(
                data=data,
                prim=self.proj.prim,
            )
        else:
            self.supercell_set = SupercellSet(prim=self.proj.prim)

        # read scel_list.json if it exists
        path = self.enum_dir / "scel_list.json"
        data = read_optional(path, default=None)
        if data is not None:
            from libcasm.configuration.io import supercell_list_from_data

            self.supercell_list = supercell_list_from_data(
                data_list=data,
                prim=self.proj.prim,
                supercells=self.supercell_set,
            )
        else:
            self.supercell_list = []

        # read config_set.json if it exists
        path = self.enum_dir / "config_set.json"
        data = read_optional(path, default=None)
        if data is not None:
            self.configuration_set = ConfigurationSet.from_dict(
                data=data,
                supercells=self.supercell_set,
            )
        else:
            self.configuration_set = ConfigurationSet()

        # read config_list.json if it exists
        path = self.enum_dir / "config_list.json"
        data = read_optional(path, default=None)
        if data is not None:
            from libcasm.configuration.io import configuration_list_from_data

            self.configuration_list = configuration_list_from_data(
                data_list=data,
                prim=self.proj.prim,
                supercells=self.supercell_set,
            )
        else:
            self.configuration_list = []

    def merge(self, src_data: "EnumData"):
        """Merge enumeration data from another EnumData object into this one"""

        # merge supercell set
        for record in src_data.supercell_set:
            self.supercell_set.add(record)

        if src_data.supercell_list is not None:
            if self.supercell_list is None:
                self.supercell_list = []
            for supercell in src_data.supercell_list:
                if supercell not in self.supercell_list:
                    self.supercell_list.append(supercell)

        if src_data.configuration_set:
            if self.configuration_set is None:
                self.configuration_set = ConfigurationSet()
            for record in src_data.configuration_set:
                self.configuration_set.add(record)

        if src_data.configuration_list:
            for configuration in src_data.configuration_list:
                if configuration not in self.configuration_list:
                    self.configuration_list.append(configuration.copy())

    def commit(self, verbose: bool = True):
        """Write the enumeration data to files in the enumeration directory

        If the data does not exist in this object, this will erase the associated
        files if they do exist.
        """
        quiet = not verbose
        self.enum_dir.mkdir(parents=True, exist_ok=True)

        path = self.enum_dir / "meta.json"
        if len(self.meta) > 0:
            if not isinstance(self.meta, dict):
                raise TypeError(
                    "Error in EnumData.commit: EnumData.meta must be a dict"
                )
            safe_dump(
                data=self.meta,
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

        path = self.enum_dir / "scel_set.json"
        if len(self.supercell_set) > 0:
            safe_dump(
                data=self.supercell_set.to_dict(),
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

        path = self.enum_dir / "scel_list.json"
        if len(self.supercell_list) > 0:
            from libcasm.configuration.io import supercell_list_to_data

            safe_dump(
                data=supercell_list_to_data(self.supercell_list),
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

        path = self.enum_dir / "config_set.json"
        if len(self.configuration_set) > 0:
            safe_dump(
                data=self.configuration_set.to_dict(),
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

        path = self.enum_dir / "config_list.json"
        if len(self.configuration_list) > 0:
            from libcasm.configuration.io import configuration_list_to_data

            safe_dump(
                data=configuration_list_to_data(self.configuration_list),
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

    def supercells_by_volume(
        self,
        max: int,
        min: int = 1,
        unit_cell: Optional[np.ndarray] = None,
        dirs: str = "abc",
        diagonal_only: bool = False,
        fixed_shape: bool = False,
        id: Optional[str] = None,
        verbose: bool = True,
        dry_run: bool = False,
    ):
        """Enumerate supercells by volume (multiples of the primitive cell volume)

        Notes
        -----

        - Results are stored in the CASM project at
          `<project>/enumerations/enum.<id>/scel_set.json`.
        - Results are stored in a :class:`~libcasm.configuration.SupercellSet`.
        - If there is an existing supercell set, the new supercells are inserted in the
          existing set.


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
            `<project>/enumerations/enum.<id>/`. If None, an id is generated
            automatically as f"supercells_by_volume.{i}", where `i` is the first
            available integer. The id can be obtained from `project.enum.last_id`.
        verbose: bool = True
            If True, print verbose output.
        dry_run: bool = False
            If True, do not save the results.
        """

        prim = self.proj.prim
        prefix = ""
        if verbose:
            if dry_run:
                prefix = "(dry run) "
            print(f"{prefix}-- Begin: Enumerating supercells by volume --")
            print()
        scel_enum = ScelEnum(prim=prim)
        n_enumerated = 0
        n_new = 0
        n_existing = 0
        size = len(self.supercell_set)
        n_init = size
        for supercell in scel_enum.by_volume(
            max=max,
            min=min,
            unit_cell=unit_cell,
            dirs=dirs,
            diagonal_only=diagonal_only,
            fixed_shape=fixed_shape,
        ):
            record = self.supercell_set.add(supercell)
            if verbose:
                n_enumerated += 1
                if len(self.supercell_set) == size:
                    n_existing += 1
                    existed = " (already existed)"
                else:
                    n_new += 1
                    existed = ""
                print(f"{prefix}  Generated: {record.supercell_name}{existed}")

        if verbose:
            print(f"{prefix}  DONE")
            print()

        if verbose:
            print(f"{prefix}-- Summary --")
            print()
            print(f"{prefix}  Initial number of supercells: {n_init}")
            print(f"{prefix}  Final number of supercells: {len(self.supercell_set)}")
            print(
                f"{prefix}  Enumerated {n_enumerated} supercells "
                f"({n_new} new, {n_existing} existing)."
            )
            print()

        if not dry_run:
            self.commit(verbose=verbose)

    def occ_by_supercell(
        self,
        max: int,
        min: int = 1,
        unit_cell: Optional[np.ndarray] = None,
        dirs: str = "abc",
        diagonal_only: bool = False,
        fixed_shape: bool = False,
        skip_non_primitive: bool = True,
        skip_non_canonical: bool = True,
        filter_f: Optional[Callable[[Configuration, "EnumData"], bool]] = None,
        continue_f: Optional[Callable[[Configuration, "EnumData"], bool]] = None,
        n_per_commit: int = 100000,
        verbose: bool = True,
        dry_run: bool = False,
    ):
        """Enumerate configuration occupation orderings by supercell volume (multiples
        of the primitive cell volume)

        Notes
        -----

        - Results are stored in the CASM project at
          `<project>/enumerations/enum.<id>/config_set.json`.
        - Results are stored in a :class:`~libcasm.configuration.ConfigurationSet`.
        - If there is an existing supercell set, the new supercells are inserted in the
          existing set.


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
        skip_non_primitive: bool = True
            If True, enumeration skips non-primitive configurations. All DoF are
            included in the check for primitive configurations.
        skip_non_canonical: bool = True
            If True, enumeration skips non-canonical configurations with respect
            to the symmetry operations that leave the supercell lattice vectors
            invariant.
        filter_f: Optional[Callable[[Configuration, EnumData], bool]] = None
            A custom filter function which, if provided, should return True to keep
            a configuration, or False to skip. The arguments are the current
            configuration and the current enumeration data. The default `filter_f`
            always returns True.
        continue_f: Optional[Callable[[Configuration, EnumData, bool], bool]] = None
            A custom function which, if provided, returns True to continue enumeration,
            or False to stop the enumeration early. The `continue_f` is called after
            each configuration is either added or skipped based on the value of
            `filter_f`. The arguments are the current enumerated configuration, the
            current enumeration data, and a bool equal to the value returned by
            `filter_f` indicating if the configuration was added to the enumeration
            data. The default `continue_f` always returns True.
        n_per_commit: int = 100000,
            The number of configurations to enumerate before committing the results.
        verbose: bool = True
            If True, print verbose output.
        dry_run: bool = False
            If True, do not save the results.
        """

        if continue_f is None:

            def continue_f(
                config: Configuration, enum: "EnumData", filter_f_value: bool
            ):
                return True

        config_enum = ConfigEnumAllOccupations(
            prim=self.proj.prim,
            supercell_set=self.supercell_set,
        )

        def print_steps_f(runner):
            record = SupercellRecord(runner.config_enum.background.supercell)
            print(f"Enumerate configurations for: {record.supercell_name}")
            sys.stdout.flush()

        runner = ConfigEnumRunner(
            config_enum=config_enum,
            curr=self,
            desc="Enumerating occupations by supercell",
            filter_f=filter_f,
            n_per_commit=n_per_commit,
            print_steps_f=print_steps_f,
            verbose=verbose,
            dry_run=dry_run,
        )
        runner.begin()
        for configuration in config_enum.by_supercell(
            max=max,
            min=min,
            unit_cell=unit_cell,
            dirs=dirs,
            diagonal_only=diagonal_only,
            fixed_shape=fixed_shape,
            skip_non_primitive=skip_non_primitive,
            skip_non_canonical=skip_non_canonical,
        ):
            filter_f_value = runner.check(configuration)
            if not continue_f(configuration, self, filter_f_value):
                break
        runner.finish()

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

    # TODO:
    # def strain_by_grid_coordinates(
    #     self,
    # ):
    #     print("strain_by_grid_coordinates")
    #     return None
    #
    # def strain_by_grid_range(
    #     self,
    # ):
    #     print("strain_by_grid_range")
    #     return None
    #
    # def strain_by_irreducible_wedge(
    #     self,
    # ):
    #     print("strain_by_irreducible_wedge")
    #     return None
    #
    # def disp_by_grid_coordinates(
    #     self,
    # ):
    #     print("disp_by_grid_coordinates")
    #     return None
