import pathlib
import sys
from typing import TYPE_CHECKING, Callable, Optional, Union

import numpy as np

from casm.project import (
    ClexDescription,
)
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

from ._ConfigEnumRunner import ConfigEnumRunner
from ._ConfigSelection import ConfigSelection

if TYPE_CHECKING:
    from casm.project import Project


class EnumData:
    """Data structure for enumeration data in a CASM project

    The CASM project enumeration directory structure:

    .. code-block:: none

        <project>/
        └── enumerations/
            └── enum.<id>/
                ├── kmc_events/
                │   └── event.<id>/
                │       ├── equivalents_info.json
                │       ├── event.json
                │       └── local_configuration_list.json
                ├── training_data/
                ├── meta.json
                ├── scel_set.json
                ├── scel_list.json
                ├── config_set.json
                └── config_list.json

    The particular files required in an enumeration directory depends on the enumeration
    method. If a file exists, it will be read in to the corresponding
    EnumData attribute on construction.

    The file `scel_set.json` is used to store a SupercellSet. The file `scel_list.json`
    is used to store a list of supercells. The file `config_set.json` is used to store a
    ConfigurationSet. The file `config_list.json` is used to store a list of
    configurations.

    An optional `meta.json` file can be used to store a description of the enumeration
    and other custom information. If "desc" is found in `meta`, it will be printed by
    `print`.

    .. rubric Using enumerations to set up calculations

    The directory `training_data` is a standard location for generating input files
    for calculations based on the enumerated configurations. The training data
    directory has the standard structure:

    .. code-block:: none

        training_data/
            └── calctype.<calctype_id>/
                └── <configname>/
                    ├── (calculation specific input & output files)
                    ├── POS
                    ├── config.json
                    ├── structure.json
                    └── structure_with_properties.json

    The `calculation_settings` directory is a standard location for storing calculation
    settings for a particular calculation type inside a CASM project directory:

    .. code-block:: none

        <project>/
        └── calculation_settings/
            └── calctype.<calctype_id>/



    """

    def __init__(self, proj: "Project", id: str):
        """

        .. rubric:: Constructor

        The EnumData object is constructed and all enumeration data is loaded. If the
        `scel_set.json` file does not exist, an empty SupercellSet is created. Other
        enumeration data is optional. To save any changes to the enumeration data, use
        the `commit` method.

        Parameters
        ----------
        proj: casm.project.Project
            The CASM project
        id: str
            The enumeration identifier. Enumeration data is stored in the enumeration
            directory at `<project>/enumerations/enum.<id>/`.
        """

        self.proj = proj
        """casm.project.Project: CASM project"""

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
        from libcasm.enumerate import ScelEnum

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

        from libcasm.enumerate import ConfigEnumAllOccupations

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

    def config_selection(
        self,
        name: str,
        clex: Union[str, ClexDescription, None] = None,
        gz: bool = False,
        records: Union[list[dict], None] = None,
    ) -> "ConfigSelection":
        """Make a ConfigSelection

        A :class:`~casm.project.enum.ConfigSelection` is a selection of configurations
        from the enumeration. It allows for easily iterating over all configurations
        in the enumeration, including configurations saved in both the
        :py:attr:`~EnumData.configuration_set` and
        :py:attr:`~EnumData.configuration_list`. Iterating over a
        :class:`~casm.project.enum.ConfigSelection` yields
        :class:`~casm.project.enum.ConfigSelectionRecord` which can use project data
        to give easy access to configuration properties such as the parametric
        composition, correlations, and calculated properties.


        Parameters
        ----------
        name : str
            The name of the configuration selection. This is used to save the selection
            to a JSON file. For example, if `name` is "main", the selection is
            saved as in the enumeration directory as `config_selection.main.json`.
            A newly created ConfigSelection is not saved to disk until
            :func:`ConfigSelection.commit` is called.

        clex : Union[str, ClexDescription, None] = None
            Specifies the default cluster expansion settings to use when getting
            properties, working with calculations, calculating basis functions, etc.

            By default, the project's default cluster expansion is used. If a
            string is provided, it should be the name of a cluster expansion included in
            the :py:data:`ProjectSettings.cluster_expansions` dictionary of the
            project's settings. Otherwise, a custom :class:`ClexDescription` can be
            provided.

        gz : bool = False
            When constructing a new selection, if True, the selection is saved as a
            gzipped JSON file. If False (default), it is saved as a regular JSON file.
            If the selection already exists in files, this is ignored and detected from
            the file extension.

        records : Optional[list[dict]] = None
            When constructing a new selection, this may be used to initialize the
            selection. If the selection is already saved to a file, this is ignored and
            the records are read from the file. By default, a new selection is
            constructed with all configurations included and selected. If provided,
            it should be a list of dict:

            .. code-block:: Python

                [
                    {
                        "source": "config_set.json",
                        "name": "SCEL1_1_1_1_0_0_0/0",
                        "selected": True,
                        ...
                    },
                    {
                        "source": "config_list.json",
                        "name": "config_list/0",
                        "selected": True,
                        ...
                    }
                ]

            The records require "source", "name", and "selected" keys. Additional
            keys may be included.


        Returns
        -------
        selection: ConfigSelection
            The ConfigSelection object.

        """
        return ConfigSelection(enum=self, name=name, clex=clex, gz=gz, records=records)

    def all_config_selections(self):
        """Return all configuration selections saved in the enumeration directory

        Returns
        -------
        selections: list[str]
            A list of configuration selection names, e.g. ["main", "all", "test"].
            These correspond to files in the enumeration directory with names like
            `config_selection.main.json`, `config_selection.all.json`, etc.
        """

        # list <name> for all files in the enumeration directory that match the
        # pattern: config_selection.<name>.json or config_selection.<name>.json.gz
        import os
        import re

        selections = set()
        pattern = re.compile(r"^config_selection\.(.+?)\.json(\.gz)?$")

        for filename in os.listdir(self.enum_dir):
            path = self.enum_dir / filename
            if not path.is_file():
                continue

            match = pattern.match(filename)
            if not match:
                continue

            selections.add(match.group(1))

        return sorted(list(selections))

    def calctype_dir(
        self,
        calctype_id: str,
    ) -> pathlib.Path:
        """Return the directory for a specific calculation type in the enumeration

        Parameters
        ----------
        calctype_id: str
            The calculation type identifier.

        Returns
        -------
        pathlib.Path
            The path to the calculation type directory in the enumeration, e.g.
            `<project>/enumerations/enum.<id>/training_data/calctype.<calctype_id>/`.
        """
        return self.proj.dir.enum_calctype_dir(enum=self.id, calctype=calctype_id)

    def compress_training_data(
        self,
        calctype_id: Optional[str] = None,
        remove_dir: bool = True,
        extension: str = ".tgz",
    ):
        """Compress training data into a tar gzipped archive file, if it exists

        Parameters
        ----------
        calctype_id: Optional[str] = None
            If provided, the training data directory for a particular calctype is
            compressed into tar gzipped archive file named
            `<project>/enumerations/enum.<id>/training_data/calctype.<calctype_id>.tgz`.
            If not provided, all training data is compressed into a file
            named `<project>/enumerations/enum.<id>/training_data.tgz`.
        remove_dir: bool = True
            If True, removes the original training data directory after compression.
            If False, keeps the original directory.
        extension: str = ".tgz"
            The file extension for the compressed archive file. Default is ".tgz".

        """
        from casm.tools.shared.file_utils import compress

        if calctype_id is None:
            dir = self.enum_dir / "training_data"
        else:
            dir = self.calctype_dir(calctype_id=calctype_id)
        if not dir.exists():
            return
        compress(
            dir=dir,
            quiet=True,
            remove_dir=remove_dir,
            extension=extension,
        )

    def uncompress_training_data(
        self,
        calctype_id: Optional[str] = None,
        remove_tgz_file: bool = True,
    ):
        """Uncompress training data from a tar gzipped archive file

        Parameters
        ----------
        calctype_id: Optional[str] = None
            If provided, the training data directory for a particular calctype is
            uncompressed from a file named
            `<project>/enumerations/enum.<id>/training_data/calctype.<calctype_id>.tgz`.
            If not provided, all training data is uncompressed from a file
            named `<project>/enumerations/enum.<id>/training_data.tgz`.
        remove_tgz_file: bool = True
            If True, removes the original tar gzipped archive file after uncompression.
            If False, keeps the original file.

        """
        from casm.tools.shared.file_utils import uncompress

        if calctype_id is None:
            tgz_file = self.enum_dir / "training_data.tgz"
        else:
            tgz_file = pathlib.Path(
                str(self.calctype_dir(calctype_id=calctype_id)) + ".tgz"
            )
        if not tgz_file.exists():
            return
        uncompress(
            tgz_file=tgz_file,
            quiet=True,
            remove_tgz_file=remove_tgz_file,
        )

    # TODO:
    # def occ_by_supercell_list(
    #         self,
    # ):
    #     print("occ_by_supercell_list")
    #     return None
    #
    # def occ_by_cluster(
    #         self,
    # ):
    #     print("occ_by_cluster")
    #     return None
    #
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
