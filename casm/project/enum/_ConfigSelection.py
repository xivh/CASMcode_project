from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, Any, Optional, Union

import numpy as np

import libcasm.xtal as xtal
from casm.project import (
    ClexDescription,
)
from casm.project.json_io import (
    read_required,
    safe_dump,
)
from libcasm.configuration import Configuration

if TYPE_CHECKING:
    from ._EnumData import EnumData


class ConfigSelectionRecord:
    """A ConfigSelection record.

    This class is provided when iterating over a :class:`ConfigSelection`.

    Notes
    -----
    - The record contains a :py:attr:`~ConfigSelectionRecord.data` dictionary, which is
      a reference to an element of the `records` list in a :class:`ConfigSelection`.
    - The record may be modified by modifying the :py:attr:`~ConfigSelectionRecord.data`
      dictionary or the using :func:`set` method to change the selection status or to
      add or remove custom key-value pairs, but changes are not saved to disk until
      `commit()` is called on the parent :class:`ConfigSelection`.
    - The :py:attr:`~ConfigSelectionRecord.data` dictionary should not be reassigned,
      because that will not update the original record data.

    """

    def __init__(self, parent: ConfigSelection, data: dict):

        self.parent: ConfigSelection = parent
        """ConfigSelection: The parent configuration selection that this record belongs
        to. 
        
        This is used to access context such as the default calctype_id."""

        self.data: dict = data
        """dict: The configuration selection record data. 
        
        This is a reference to an element of the `records` list in a
        :class:`ConfigSelection`. The dictionary may be modified to change the
        selection status or to add or remove custom key-value pairs, but changes are 
        not saved to disk until `commit()` is called on the parent 
        :class:`ConfigSelection`.
        
        The :py:attr:`ConfigSelectionRecord.data` dictionary should not be reassigned,
        because it is a reference to the original record data.
        """

        if "source" not in data:
            raise ValueError("Configuration selection record must have a 'source' key.")
        if "name" not in data:
            raise ValueError("Configuration selection record must have a 'name' key.")
        if "selected" not in data:
            raise ValueError(
                "Configuration selection record must have a 'selected' key."
            )

    @property
    def _enum(self) -> "EnumData":
        """EnumData: The EnumData for the enumeration the parent selection belongs
        to."""
        return self.parent._enum

    @property
    def source(self) -> str:
        """str: The source of the configuration. One of `config_set.json` or
        `config_list.json`."""
        return self.data["source"]

    @property
    def name(self) -> str:
        """str: The name of the configuration."""
        return self.data["name"]

    @property
    def is_selected(self) -> bool:
        """bool: Whether the configuration is selected."""
        return self.data["selected"]

    def select(self):
        """Select the configuration.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` on the
        :class:`ConfigSelection` to save the change.

        """
        self.data["selected"] = True

    def deselect(self):
        """Deselect the configuration.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` on the
        :class:`ConfigSelection` to save the change.

        """
        self.data["selected"] = False

    @property
    def configuration(self) -> Configuration:
        """libcasm.configuration.Configuration: The configuration."""
        if self.source == "config_set.json":
            return self._enum.configuration_set.get_by_name(self.name)
        elif self.source == "config_list.json":
            try:
                index = int(self.name.split("/")[-1])
                return self._enum.configuration_list[index]
            except (ValueError, IndexError) as e:
                raise ValueError(
                    f"Invalid configuration name format: {self.name}"
                ) from e
        else:
            raise ValueError(f"Unsupported source: {self.source}")

    @property
    def chemical_param_comp(self) -> np.ndarray:
        """numpy.ndarray: The parametric chemical composition of the configuration in
        the project's default chemical composition axes."""
        return self.parent._chemical_comp_calculator.param_composition(
            self.configuration
        )

    @property
    def chemical_comp_per_supercell(self) -> np.ndarray:
        """numpy.ndarray: The chemical composition of the configuration, in number per
        supercell."""
        return self.parent._chemical_comp_calculator.per_supercell(self.configuration)

    @property
    def chemical_comp_per_unitcell(self) -> np.ndarray:
        """numpy.ndarray: The chemical composition of the configuration, in number per
        unitcell."""
        return self.parent._chemical_comp_calculator.per_unitcell(self.configuration)

    @property
    def chemical_comp_species_frac(self) -> np.ndarray:
        """numpy.ndarray: The chemical composition of the configuration, in species
        fraction, with [Va] = 0.0"""
        return self.parent._chemical_comp_calculator.species_frac(self.configuration)

    def chemical_sublat_comp_per_supercell(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate chemical sublattice composition per supercell.

        Returns
        -------
        value: numpy.ndarray
            The chemical composition of the configuration, in number per
            supercell, on the requested sublattice.
        """
        return self.parent._chemical_comp_calculator.per_supercell(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    def chemical_sublat_comp_per_unitcell(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate chemical sublattice composition per unitcell.

        Returns
        -------
        value: numpy.ndarray
            The chemical composition of the configuration, in number per
            unitcell, on the requested sublattice.
        """
        return self.parent._chemical_comp_calculator.per_unitcell(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    def chemical_sublat_comp_species_frac(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate chemical sublattice composition as species fraction, with
        [Va] = 0.0

        Returns
        -------
        value: numpy.ndarray
            The chemical composition of the configuration, in species fraction, with
            [Va] = 0.0, on the requested sublattice.
        """
        return self.parent._chemical_comp_calculator.species_frac(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    @property
    def occupant_param_comp(self) -> np.ndarray:
        """numpy.ndarray: The parametric occupant composition of the configuration in
        the project's default occupant composition axes."""
        return self.parent._occupant_comp_calculator.param_composition(
            self.configuration
        )

    @property
    def occupant_comp_per_supercell(self) -> np.ndarray:
        """numpy.ndarray: The occupant composition of the configuration, in number per
        supercell."""
        return self.parent._occupant_comp_calculator.per_supercell(self.configuration)

    @property
    def occupant_comp_per_unitcell(self) -> np.ndarray:
        """numpy.ndarray: The occupant composition of the configuration, in number per
        unitcell."""
        return self.parent._occupant_comp_calculator.per_unitcell(self.configuration)

    @property
    def occupant_comp_species_frac(self) -> np.ndarray:
        """numpy.ndarray: The occupant composition of the configuration, in species
        fraction, with [Va] = 0.0"""
        return self.parent._occupant_comp_calculator.species_frac(self.configuration)

    def occupant_sublat_comp_per_supercell(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate the occupant composition per supercell on a particular sublattice.

        Returns
        -------
        value: numpy.ndarray
            The occupant composition of the configuration, in number per
            supercell, on the requested sublattice.
        """
        return self.parent._occupant_comp_calculator.per_supercell(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    def occupant_sublat_comp_per_unitcell(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate the occupant composition per unitcell on a particular sublattice.

        Returns
        -------
        value: numpy.ndarray
            The occupant composition of the configuration, in number per
            unitcell, on the requested sublattice.
        """
        return self.parent._occupant_comp_calculator.per_unitcell(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    def occupant_sublat_comp_species_frac(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate the occupant composition as species fraction, with [Va] = 0.0
        on a particular sublattice.

        Returns
        -------
        value: numpy.ndarray
            The occupant composition of the configuration, in species fraction, with
            [Va] = 0.0, on the requested sublattice.
        """
        return self.parent._occupant_comp_calculator.species_frac(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    @property
    def corr_per_unitcell(self) -> Optional[np.ndarray]:
        """Optional[numpy.ndarray]: The correlations of the configuration per unitcell,
        if a basis set exists."""
        _corr_calculator = self.parent._corr_calculator
        if _corr_calculator is None:
            return None

        return _corr_calculator.per_unitcell(self.configuration)

    @property
    def corr_per_supercell(self) -> Optional[np.ndarray]:
        """Optional[numpy.ndarray]: The correlations of the configuration per supercell,
        if a basis set exists."""
        _corr_calculator = self.parent._corr_calculator
        if _corr_calculator is None:
            return None

        return _corr_calculator.per_supercell(self.configuration)

    @property
    def calc_dir(self) -> Optional[pathlib.Path]:
        """Optional[pathlib.Path]: The calculation directory for this configuration,
        if a `clex` is given for the parent selection."""
        if self.parent.clex is None:
            return None

        return self._enum.proj.dir.enum_calc_dir(
            enum=self._enum.id,
            calctype=self.parent.clex.calctype,
            configname=self.name,
        )

    @property
    def is_calculated(self) -> bool:
        """bool: Whether the configuration has been calculated, as determined by
        checking for the presence of a `structure_with_properties.json` file in the
        configuration's calculation directory.

        .. warning::

            This does not check for custom structures that are equivalent to the
            configuration, other enumerations with equivalent configurations,
            configurations that relaxed to this configuration, configurations that have
            been calculated with different calculation type settings, etc.

        """
        calc_dir = self.calc_dir
        if calc_dir is None:
            return False

        structure_file = calc_dir / "structure_with_properties.json"
        return structure_file.exists()

    @property
    def structure_with_properties(self) -> Optional[xtal.Structure]:
        """Optional[xtal.Structure]: The structure with properties for the
        configuration, if it has been calculated, and saved in a
        `structure_with_properties.json` file in the configuration's calculation
        directory.

        Is None if the configuration has not been calculated or if the
        calculation directory does not exist.

        .. warning::

            This does not check for custom structures that are equivalent to the
            configuration, other enumerations with equivalent configurations,
            configurations that relaxed to this configuration, configurations that have
            been calculated with different calculation type settings, etc.

        """
        calc_dir = self.calc_dir
        if calc_dir is None:
            return False

        structure_file = calc_dir / "structure_with_properties.json"
        if not structure_file.exists():
            return None
        return xtal.Structure.from_dict(read_required(structure_file))

    def set(self, key: str, value: Any):
        """Set a custom key-value pair in the record.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` on the
        :class:`ConfigSelection` to save the change.

        Parameters
        ----------
        key : str
            The key to set.
        value : Any
            The value to set for the key. The value should be JSON serializable.
        """
        self.data[key] = value

    def get(self, key: str, default_value: Any = None) -> Any:
        """Get the value of a custom key-value pair from the record.

        Parameters
        ----------
        key : str
            The key to get.
        default_value : Any = None
            The default value to return if the key does not exist. Defaults to None.

        Returns
        -------
        Any
            The value associated with the key.
        """
        return self.data.get(key, default_value)


class ConfigSelection:
    """A selection of configurations from an enumeration.

    This class helps to select configurations from an enumeration and to query data,
    setup calculations, retrieve calculation results, calculate correlations, fit
    cluster expansion coefficients, etc.

    Notes
    -----

    - Selections are saved to a JSON file in the enumeration directory, allowing
      reuse. The file is named `config_selection.<name>.json` or
      `config_selection.<name>.json.gz`, if the compression option `gz` is set to True.
    - Selections are typically constructed and used via the
      :func:`EnumData.config_selection` method.
    - To save a newly constructed or modified selection, call the
      :func:`Selection.commit` method.

    .. rubric:: Special Methods

    - ``for record in selection``: Iterate over selected configurations, yielding
      :class:`ConfigSelectionRecord` for each selected configuration.


    """

    def __init__(
        self,
        enum: "EnumData",
        name: str,
        clex: Union[str, ClexDescription, None] = None,
        gz: bool = False,
        records: Union[list[dict], None] = None,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        enum : EnumData
            The enumeration data.

        name : str
            The name of the configuration selection. This is used to save the selection
            to a JSON file. For example, if `name` is "main", the selection is
            saved as in the enumeration directory as `config_selection.main.json`.

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
            selection. If the selection already is saved to a file, this is ignored and
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

        """
        self._enum: "EnumData" = enum
        """EnumData: The enumeration data containing configuration sets and lists."""

        self.name: str = name
        """str: The name of the configuration selection. 
        
        This is used to save the selection to a JSON file. For example, if `name` is 
        "main", the selection is saved as in the enumeration directory as 
        `config_selection.main.json`."""

        # Initialize the default cluster expansion ClexDescription

        if clex is None:
            # Use the default cluster expansion from the enumeration's project settings
            clex = self._enum.proj.settings.default_clex
        elif isinstance(clex, str):
            cluster_expansions = self._enum.proj.settings.cluster_expansions
            if clex not in cluster_expansions:
                raise ValueError(
                    f"Cluster expansion '{clex}' not found in project settings."
                )

            clex = cluster_expansions.get(clex)
        elif not isinstance(clex, ClexDescription):
            raise TypeError(
                f"Expected clex to be None, a string, or a ClexDescription, "
                f"got {type(clex)}"
            )

        self.clex: Optional[ClexDescription] = clex
        """Optional[ClexDescription]: The default cluster expansion settings to
        use when getting properties, working with calculations, etc., if present.
        """

        # Read existing records from file if available,
        # otherwise if records are provided, use those,
        # otherwise initialize with all configurations selected

        self._path = (
            pathlib.Path(self._enum.proj.dir.enum_dir(self._enum.id))
            / f"config_selection.{self.name}.json"
        )
        self._path_gz = (
            pathlib.Path(self._enum.proj.dir.enum_dir(self._enum.id))
            / f"config_selection.{self.name}.json.gz"
        )

        if self._path_gz.exists():
            self._gz = True
            records = read_required(path=self._path_gz, gz=True)
        elif self._path.exists():
            self._gz = False
            records = read_required(path=self._path)
        elif records is None:
            self._gz = gz
            records = []

            for record in self._enum.configuration_set:
                # Select all configurations by default
                records.append(
                    {
                        "source": "config_set.json",
                        "name": record.configuration_name,
                        "selected": True,
                    }
                )

            for i, config in enumerate(self._enum.configuration_list):
                # Select all configurations by default
                records.append(
                    {
                        "source": "config_list.json",
                        "name": f"config_list/{i}",
                        "selected": True,
                    }
                )
        else:
            self._gz = gz

        self._records: list[dict] = records
        """list[dict]: Records of selected configurations. Each record is a dict with
        "source", "name", and "selected" keys. Additional keys may be present."""

        # Initialize the index mapping for fast access by name

        self._index_by_name: dict[str, int] = {}
        for i, record in enumerate(self._records):
            name = record["name"]
            if name in self._index_by_name:
                raise ValueError(
                    f"Duplicate configuration name found in records: {name}"
                )
            self._index_by_name[name] = i
        """dict[str, int]: Index of each configuration record by its name."""

        # Initialize the chemical and occupant composition calculators for the default
        # project chemical and occupant composition axes

        self._chemical_comp_calculator = self._enum.proj.make_chemical_comp_calculator()
        """ConfigCompositionCalculator: Chemical composition calculator using the
        default project chemical composition axes.
        
        The "chemical composition" treats all :class:`~libcasm.xtal.Occupant` that
        have the same "chemical name" (:func:`~libcasm.xtal.Occupant.name`) as a
        single component, even if they have different magnetic spin, molecular
        orientation, etc."""

        self._occupant_comp_calculator = self._enum.proj.make_occupant_comp_calculator()
        """ConfigCompositionCalculator: Occupant composition calculator using the
        default project occupant composition axes.
        
        The "occupant composition" treats all :class:`~libcasm.xtal.Occupant` that
        have different magnetic spin, molecular orientation, etc. as distinct
        components.
        """

        # Initialize the correlation calculator for the default cluster expansion
        _corr_calculator = None
        if self.clex is not None:
            bset = self._enum.proj.bset.get(id=self.clex.bset)
            try:
                _corr_calculator = bset.make_corr_calculator()
            except Exception as e:
                if "No basis.json" not in str(e):
                    raise

        self._corr_calculator = _corr_calculator
        """Optional[ConfigCorrCalculator]: The correlations calculator for the default 
        cluster expansion's bset, if available."""

    @property
    def path(self) -> pathlib.Path:
        """pathlib.Path: The path to the configuration selection file."""
        return self._path if not self._gz else self._path_gz

    def commit(self):
        """Save selection to file."""
        safe_dump(
            data=self._records,
            path=self.path,
            force=True,
            quiet=True,
            gz=self._gz,
        )

    @property
    def chemical_components(self) -> list[str]:
        """list[str]: The order of components in chemical composition vector
        results."""
        return self._chemical_comp_calculator.components

    @property
    def occupant_components(self) -> list[str]:
        """list[str]: The order of components in occupant composition vector
        results."""
        return self._occupant_comp_calculator.components

    def get(self, name: str) -> Optional[ConfigSelectionRecord]:
        """Get a record by name.

        Parameters
        ----------
        name : str
            The name of the configuration selection record.

        Returns
        -------
        result: Optional[ConfigSelectionRecord]
            The configuration selection record if found, otherwise None.
        """
        index = self._index_by_name.get(name)
        if index is not None:
            return ConfigSelectionRecord(parent=self, data=self._records[index])
        return None

    def select(self, name: str):
        """Select a configuration by name.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        name : str
            The name of the configuration to select.
        """
        record = self.get(name)
        if record is not None:
            record.selected = True
        else:
            raise ValueError(f"Configuration '{name}' not found in selection.")

    def select_all(self):
        """Select all configurations in the selection.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.
        """
        for record in self._records:
            record["selected"] = True

    def deselect(self, name: str):
        """Deselect a configuration by name.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        name : str
            The name of the configuration to deselect.
        """
        record = self.get(name)
        if record is not None:
            record.selected = False
        else:
            raise ValueError(f"Configuration '{name}' not found in selection.")

    def deselect_all(self):
        """Deselect all configurations in the selection.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.
        """
        for record in self._records:
            record["selected"] = False

    def erase(self, name_or_names: Union[str, list[str]]):
        """Erase a configuration record by name.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        name_or_names : Union[str, list[str]]
            The name of the configuration to erase, or a list of names to erase.
            If a list is provided, all specified configurations are removed.

            If multiple configurations are going to be erased, it is preferable
            to erase them in a single call so that the name to index table is only
            rebuilt once.

            Configurations should not be erased while iterating over the selection.
        """
        if isinstance(name_or_names, str):
            name_or_names = [name_or_names]

        for name in name_or_names:
            index = self._index_by_name.pop(name, None)
            if index is not None:
                del self._records[index]
            else:
                raise ValueError(f"Configuration '{name}' not found in selection.")

        # Update the index mapping after all deletions
        self._index_by_name = {rec["name"]: i for i, rec in enumerate(self._records)}

    def insert(
        self,
        name: str,
        source: str,
        selected: bool = True,
        **kwargs,
    ):
        """Insert a new configuration record into the selection.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        name : str
            The name of the configuration. Should be
            :py:attr:`ConfigurationRecord.configuration_name` for members of
            the enumeration's configuration set, or a string like "config_list/0" for
            members of the enumeration's configuration list.
        source : str
            The source of the configuration, either "config_set.json" or
            "config_list.json".
        selected : bool = True
            Whether the configurations added are selected or not selected.
        **kwargs : Any
            Additional key-value pairs to include in the record. These should be
            JSON serializable.

        Raises
        ------
        ValueError
            If the source is not one of "config_set.json" or "config_list.json", or if
            the configuration name already exists in the selection.

        """
        if source not in {"config_set.json", "config_list.json"}:
            raise ValueError(
                f"Invalid source '{source}'. "
                "Must be 'config_set.json' or 'config_list.json'."
            )

        if name in self._index_by_name:
            raise ValueError(f"Configuration '{name}' already exists in selection.")

        record = {
            "source": source,
            "name": name,
            "selected": selected,
            **kwargs,
        }
        self._records.append(record)
        self._index_by_name[name] = len(self._records) - 1

    def insert_all(
        self,
        selected: bool = True,
    ):
        """Insert all configurations from the enumeration into the selection that are
        not already present.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        selected : bool = True
            Whether the configurations added are selected or not selected.
            Defaults to True, meaning all configurations inserted are selected.
        """
        source = "config_set.json"
        for record in self._enum.configuration_set:
            if record.configuration_name not in self._index_by_name:
                self.insert(
                    name=record.configuration_name,
                    source=source,
                    selected=selected,
                )

        source = "config_list.json"
        for i, config in enumerate(self._enum.configuration_list):
            name = f"config_list/{i}"
            if name not in self._index_by_name:
                self.insert(
                    name=name,
                    source=source,
                    selected=selected,
                )

    def __len__(self) -> int:
        """Return the number of configuration records in the selection."""
        return len(self._records)

    def __iter__(self):
        """Iterate over the selected configuration records."""
        for record in self._records:
            yield ConfigSelectionRecord(parent=self, data=record)
