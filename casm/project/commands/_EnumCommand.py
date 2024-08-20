import sys
from typing import Callable, Optional

import numpy as np

from casm.project._ConfigEnumRunner import _ConfigEnumRunner
from casm.project._EnumData import EnumData
from casm.project._Project import Project
from libcasm.configuration import (
    Configuration,
    SupercellRecord,
)
from libcasm.enumerate import (
    ConfigEnumAllOccupations,
    ScelEnum,
)


class EnumCommand:
    """Methods to enumerate supercells, configurations, events, etc."""

    def __init__(self, proj: Project):
        self.proj = proj
        """Project: CASM project."""

        self.last = None
        """Optional[EnumData]: Data from the last enumeration operation."""

    def _new_id(self, id_base: str):
        """Return id=f"{id_base}.{i}" where `i` is the first available integer,
        starting with 0

        Parameters
        ----------
        id_base : str
            The base name for the identifier, such as "supercells_by_volume".

        Returns
        -------
        id : str
            The new identifier string
        """
        i = 0
        id = f"{id_base}.{i}"
        while self.proj.dir.enum_dir(id).exists():
            i += 1
            id = f"{id_base}.{i}"
        return id

    def all(self):
        """Return the identifiers of all enumerations

        Returns
        -------
        all_enum: list[str]
            A list of enumeration identifiers
        """
        return self.proj.dir.all_enum()

    def list(self):
        """Print all enumerations"""
        for id in self.all():
            enum = self.get(id)
            print(enum)

    def get(self, id: str):
        """Load enumeration data

        Parameters
        ----------
        id : str
            The enumeration identifier

        Returns
        -------
        enum: EnumData
            The enumeration data
        """
        return EnumData(proj=self.proj, id=id)

    def remove(self, id: str):
        """Remove enumeration data

        Parameters
        ----------
        id : str
            The enumeration identifier
        """
        import shutil

        enum_dir = self.proj.dir.enum_dir(id)
        if not enum_dir.exists():
            raise FileNotFoundError(f"Enumeration {id} does not exist.")
        shutil.rmtree(self.proj.dir.enum_dir(id))

    def copy(self, src_id: str, dest_id: str):
        """Copy enumeration data

        Parameters
        ----------
        src_id : str
            The source enumeration identifier
        dest_id : str
            The destination enumeration identifier
        """
        data = self.get(src_id)
        data.id = dest_id

        enum_dir = self.proj.dir.enum_dir(dest_id)
        enum_dir.mkdir(parents=True, exist_ok=False)
        data.enum_dir = enum_dir
        data.commit()

    def merge(self, src_id: str, dest_id: str):
        """Merge enumeration data

        Supercells and configurations in lists are appended to the destination
        enumeration if they are not already present.

        Parameters
        ----------
        src_id : str
            The source enumeration identifier
        dest_id : str
            The destination enumeration identifier

        """
        src_data = self.get(src_id)
        dest_data = self.get(dest_id)
        dest_data.merge(src_data)
        dest_data.commit()

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
        if id is None:
            id = self._new_id(id_base="supercells_by_volume")

        curr = EnumData(proj=self.proj, id=id)
        self.last = curr

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
        size = len(curr.supercell_set)
        n_init = size
        for supercell in scel_enum.by_volume(
            max=max,
            min=min,
            unit_cell=unit_cell,
            dirs=dirs,
            diagonal_only=diagonal_only,
            fixed_shape=fixed_shape,
        ):
            record = curr.supercell_set.add(supercell)
            if verbose:
                n_enumerated += 1
                if len(curr.supercell_set) == size:
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
            print(f"{prefix}  Final number of supercells: {len(curr.supercell_set)}")
            print(
                f"{prefix}  Enumerated {n_enumerated} supercells "
                f"({n_new} new, {n_existing} existing)."
            )
            print()

        if not dry_run:
            curr.commit(verbose=verbose)

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
        filter_f: Optional[Callable[[Configuration, EnumData], bool]] = None,
        continue_f: Optional[Callable[[Configuration, EnumData], bool]] = None,
        n_per_commit: int = 100000,
        id: Optional[str] = None,
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
        - After completion, the results


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

        if id is None:
            id = self._new_id(id_base="occ_by_supercell")
        if continue_f is None:

            def continue_f(config, enum_data, filter_f_value):
                return True

        curr = EnumData(proj=self.proj, id=id)
        self.last = curr

        config_enum = ConfigEnumAllOccupations(
            prim=self.proj.prim,
            supercell_set=curr.supercell_set,
        )

        def print_steps_f(runner):
            record = SupercellRecord(runner.config_enum.background.supercell)
            print(f"Enumerate configurations for: {record.supercell_name}")
            sys.stdout.flush()

        runner = _ConfigEnumRunner(
            config_enum=config_enum,
            curr=curr,
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
            if not continue_f(configuration, curr, filter_f_value):
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
