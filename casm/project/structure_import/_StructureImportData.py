import pathlib
from typing import TYPE_CHECKING, Optional

import libcasm.configuration as casmconfig
import libcasm.mapping.info as mapinfo
import libcasm.mapping.methods as mapmethods
import libcasm.xtal as xtal
from casm.project.json_io import read_optional, safe_dump

if TYPE_CHECKING:
    from casm.project import Project

# Fix:
# - lattice_mapping_from='initial_configuration', 'search', 'user',
# - atom_mapping_translation_from='search', 'zero', 'user'
# - atom_mapping_permutation_from='search', 'identity', 'user'


class StructureRecord:
    def __init__(
        self,
        structure: xtal.Structure,
        relpath: Optional[pathlib.Path] = None,
        ideal_lattice: Optional[xtal.Lattice] = None,
        ideal_structure: Optional[xtal.Structure] = None,
        ideal_configuration: Optional[casmconfig.Configuration] = None,
        mappings: Optional[list[mapinfo.ScoredStructureMapping]] = None,
        selected_mapping_index: Optional[int] = None,
        mapped_structure: Optional[xtal.Structure] = None,
        mapped_configuration: Optional[casmconfig.ConfigurationWithProperties] = None,
        data: Optional[dict] = None,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        structure: libcasm.xtal.Structure
            A structure, with or without calculated properties
        relpath: Optional[pathlib.Path] = None
            Relative path to the calculation directory, from the project directory.
        ideal_lattice: Optional[libcasm.xtal.Lattice] = None
            Ideal lattice, if known.
        ideal_structure: Optional[libcasm.xtal.Structure] = None
            Ideal structure, if known.
        ideal_configuration: Optional[libcasm.configuration.Configuration] = None
            Ideal configuration, if known.
        mappings: Optional[list[libcasm.mapping.info.ScoredStructureMapping]] = None
            Scored structure mappings.
        selected_mapping_index: Optional[int] = None
            Index into `mappings` of the selected mapping.
        mapped_structure: Optional[libcasm.xtal.Structure] = None
            Mapped structure with properties
        mapped_configuration: \
        Optional[libcasm.configuration.ConfigurationWithProperties] = None
            Mapped configuration with properties
        data: Optional[dict] = None
            Any additional JSON-serializable data describing the mapping success or
            failure.
        """
        self.structure = structure
        """libcasm.xtal.Structure: Structure, with or without calculated properties"""

        self.relpath = relpath
        """Optional[pathlib.Path]: Relative path to the calculation directory, from
        the project directory."""

        self.ideal_lattice = ideal_lattice
        """Optional[libcasm.xtal.Lattice]: Ideal lattice, if known.
        
        Depending on the import and mapping method, this may be used to constrain the 
        solution to a particular supercell, or be used as hint or starting point
        without fixing the supercell.
        """

        self.ideal_structure = ideal_structure
        """Optional[libcasm.xtal.Structure]: Ideal structure, if known.
        
        Depending on the import and mapping method, this may be used to constrain the 
        solution to a particular supercell or configuration, or be used as hint or 
        starting point without fixing the supercell.
        """

        self.ideal_configuration = ideal_configuration
        """Optional[libcasm.configuration.Configuration]: Ideal configuration, if known
        
        Depending on the import and mapping method, this may be used to constrain the 
        solution to a particular supercell or configuration, or be used as hint or 
        starting point without fixing the supercell.
        """

        self.mappings = mappings
        """Optional[list[libcasm.mapping.info.ScoredStructureMapping]]: All scored \
        structure mappings."""

        self.selected_mapping_index = selected_mapping_index
        """Optional[int]: Index into `mappings` of the selected mapping."""

        self.mapped_structure = mapped_structure
        """Optional[libcasm.xtal.Structure]: Mapped structure with properties"""

        self.mapped_configuration = mapped_configuration
        """Optional[libcasm.configuration.ConfigurationWithProperties]: Mapped \
        configuration with properties"""

        self.data = data
        """Optional[dict]: Any additional JSON-serializable data describing the 
        mapping success or failure"""

    def set_selected_mapping_index(
        self,
        index: int,
        supercells: casmconfig.SupercellSet,
        converter: str = "isotropic_atomic",
        magspin_tol: float = 1.0,
    ):
        """Set the selected mapping index and update the mapped structure and
        mapped configuration.

        Parameters
        ----------
        index: int
            Index into `mappings` of the selected mapping.
        supercells: casmconfig.SupercellSet
            The supercell set to use for generating the mapped configuration from the
            mapped structure.
        converter: str = "isotropic_atomic"
            The converter to use for generating the mapped configuration from the mapped
            structure. Options are "isotropic_atomic" or  "discrete_magnetic_atomic".
            See
            :func:`ConfigurationWithProperties.from_structure<libcasm.configuration.ConfigurationWithProperties.from_structure>`
            for a detailed description of the methods.
        magspin_tol: float = 1.0
            The tolerance for the magnetic spin moment for the
            "discrete_magnetic_atomic" converter.
        """
        if index < 0 or index >= len(self.mappings):
            raise ValueError("Index out of range")
        self.selected_mapping_index = index
        self.mapped_structure = mapmethods.make_mapped_structure(
            structure_mapping=self.mappings[index],
            unmapped_structure=self.structure,
        )
        self.mapped_configuration = (
            casmconfig.ConfigurationWithProperties.from_structure(
                prim=supercells.prim,
                structure=self.mapped_structure,
                converter=converter,
                supercells=supercells,
                magspin_tol=magspin_tol,
            )
        )

    def to_dict(self):
        """Represent a StructureRecord as a Python dict"""
        data = {
            "relpath": str(self.relpath),
            "structure": self.structure.to_dict(),
        }
        if self.ideal_lattice is not None:
            data["ideal_lattice"] = self.ideal_lattice.to_dict()
        if self.ideal_structure is not None:
            data["ideal_structure"] = self.ideal_structure.to_dict()
        if self.ideal_configuration is not None:
            data["ideal_configuration"] = self.ideal_configuration.to_dict()
        if self.mappings is not None:
            data["mappings"] = [mapping.to_dict() for mapping in self.mappings]
        if self.selected_mapping_index is not None:
            data["selected_mapping_index"] = self.selected_mapping_index
        if self.mapped_structure is not None:
            data["mapped_structure"] = self.mapped_structure.to_dict()
        if self.mapped_configuration is not None:
            data["mapped_configuration"] = self.mapped_configuration.to_dict()
        if self.data is not None:
            data["data"] = self.data
        return data

    @staticmethod
    def from_dict(data: dict, supercells: casmconfig.SupercellSet):
        """Construct a StructureRecord from a Python dict"""

        prim = supercells.prim()

        ideal_lattice = None
        if "ideal_lattice" in data:
            ideal_lattice = xtal.Lattice.from_dict(data=data["ideal_lattice"])

        ideal_structure = None
        if "ideal_structure" in data:
            ideal_structure = xtal.Structure.from_dict(data=data["ideal_structure"])

        ideal_configuration = None
        if "ideal_configuration" in data:
            ideal_configuration = casmconfig.Configuration.from_dict(
                data=data["ideal_configuration"],
                supercells=supercells,
            )

        mappings = None
        if "mappings" in data:
            mappings = [
                mapinfo.ScoredStructureMapping.from_dict(prim=prim.xtal_prim, data=mapping)
                for mapping in data["mappings"]
            ]

        mapped_structure = None
        if "mapped_structure" in data:
            mapped_structure = xtal.Structure.from_dict(data=data["mapped_structure"])

        mapped_configuration = None
        if "mapped_configuration" in data:
            mapped_configuration = casmconfig.ConfigurationWithProperties.from_dict(
                data=data["mapped_configuration"],
                supercells=supercells,
            )

        return StructureRecord(
            structure=xtal.Structure.from_dict(data["structure"]),
            id=id,
            relpath=pathlib.Path(data["relpath"]),
            ideal_lattice=ideal_lattice,
            ideal_structure=ideal_structure,
            ideal_configuration=ideal_configuration,
            mappings=mappings,
            selected_mapping_index=data.get("selected_mapping_index", None),
            mapped_structure=mapped_structure,
            mapped_configuration=mapped_configuration,
            data=data.get("data", None),
        )


class StructureImportData:
    """Data structure for structure import data in a CASM project

    The CASM project import directory structure:

    .. code-block:: none

        <project>/
        └── imports/
            └── import.<id>/
                ├── meta.json
                ├── settings.json
                ├── structures.json
                ├── structures/
                │   └── <index>/
                │       ├── mapped_structure.json
                │       └── mapped_configuration.json
                ├── configurations.json
                └──  choices.json



    The `settings.json` file contains a JSON dict with settings for structure import
    and mapping including:

    - `enum_id`: str, The identifier for an enumeration used to store imported
      configurations and supercells.
    - `map_to_canonical_form`: bool, If true, imported structures are mapped to a
      a canonical form in a canonical supercell. The imported configurations will be
      inserted into the enumeration's ConfigurationSet.
    - `map_without_reorientation`: bool, If true, imported structures are mapped to
      a configuration without reorientation. The imported configurations will be
      inserted into the enumeration's Configuration list. Note, both
      `map_to_canonical_form` and `map_without_reorientation` can be true.

    The `structures.json` file contains the structures to be imported, including
    calculated properties if available, and the mapping results once completed.

    An optional `meta.json` file can be used to store a description of the enumeration
    and other custom information. If "desc" is found in `meta`, it will be printed by
    `print`.

    """

    def __init__(self, proj: "Project", id: str, enum_id: Optional[str] = None):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        proj: casm.project.Project
            The CASM project
        id: str
            The structure import identifier. Structure import data is stored in the
            import directory at `<project>/imports/import.<id>/`.
        enum_id: Optional[str] = None
            An enumeration identifier. Mapped supercells and configurations are stored
            in the enumeration directory at `<project>/enumerations/enum.<enum_id>/`.
            The first time `StructureImportData` is constructed, an `enum_id` is
            required. Once the `StructureImportData` is saved with a `commit`, then the
            `enum_id` is stored in `settings.json`. On subsequent constructions, the
            `enum_id` will be read from `settings.json` and is not needed by the
            constructor.
        """

        self.proj = proj
        """Project: CASM project reference"""

        self.id = id
        """str: Import identifier"""

        self.import_dir = self.proj.dir.import_dir(id=id)
        """pathlib.Path: Import directory"""

        ### Data (load & commit) ###

        self.enum_id = enum_id
        """str: Enumeration identifier, for an enumeration used to store 
        imported configurations and supercells."""

        # note: this will be constructed in `load`
        self.enum = None
        """casm.project.enum.EnumData: EnumData used to store imported 
        configurations and supercells."""

        self.meta = dict()
        """dict: A description of the enumeration, read from `meta.json`."""

        self.structures: list[StructureRecord]
        """list[StructureRecord]: Structures being imported, read from 
        `structures.json`.
        
        StructureRecord stores a calculation results along with additional 
        information (ideal lattice, structure, or configuration) that may be used to 
        constrain or guide a structure mapping method. The particular way the data is
        used is not defined here, but is up to the structure mapping method. The 
        StructureRecord is stored by an str identifier."""

        # load data
        self.load()

    def load(self):
        """Read meta.json, structures.json, and enum data.

        This will replace the current contents of this StructureImportData object with
        the contents of the associated files, or set the current contents to None if the
        associated files do not exist.
        """

        # read meta.json if it exists
        path = self.import_dir / "meta.json"
        self.meta = read_optional(path, default=dict())

        # read settings.json if it exists
        path = self.import_dir / "settings.json"
        data = read_optional(path, default=None)
        if data is not None:
            # read `enum_id`
            enum_id = data.get("enum_id", None)
            if self.enum_id is not None and enum_id != self.enum_id:
                raise ValueError(
                    "Error in StructureImportData.load: "
                    "enum_id mismatch between settings.json and constructor."
                )
            self.enum_id = enum_id

            # TODO: read additional settings

        # load the enumeration data
        if self.enum_id is None:
            raise ValueError(
                "Error in StructureImportData.load: "
                "No enum_id. The enum_id must be given at construction "
                "or found in settings.json."
            )
        self.enum = self.proj.enum.get(self.enum_id)
        self.enum.load()

        # read structures.json if it exists
        path = self.import_dir / "structures.json"
        self.structures = []
        data = read_optional(path, default=list())
        for structure_data in data:
            record = StructureRecord.from_dict(
                data=structure_data, supercells=self.enum.supercell_set
            )
            self.structures.append(record)

    def commit(self, verbose: bool = True):
        """Write meta.json, structures.json, and enum data.

        If the data does not exist in this object, this will erase the associated
        files if they do exist.
        """
        quiet = not verbose
        self.import_dir.mkdir(parents=True, exist_ok=True)

        # write meta.json
        path = self.import_dir / "meta.json"
        if len(self.meta) > 0:
            if not isinstance(self.meta, dict):
                raise TypeError(
                    "Error in StructureImportData.commit: "
                    "StructureImportData.meta must be a dict"
                )
            safe_dump(
                data=self.meta,
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

        # write structures.json
        path = self.import_dir / "structures.json"
        if len(self.structures) > 0:
            data = [record.to_dict() for record in self.structures]
            safe_dump(
                data=data,
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

        # commit the enumeration data
        self.enum.commit(verbose=verbose)

    def clear(self):
        """Clear collected structures and mapping results"""
        self.structures = []

    def collect(self):
        """Search for structures to import"""
        # TODO:
        # - Look structure files, and also for files containing the ideal lattice,
        #   structure, or configuration if known
        # - Give options for where to search for structures
        #   - Could be enumeration ids of one or more enumerations to read calculations
        #     from,
        #   - Could be one or more directories to search
        # - Give options for structure files names
        #   - By default look for "properties.calc.json", but perhaps a different name
        #     is used
        # - For each structure found, create a StructureRecord in self.structures
        #
        # Question:
        # - Is it preferable to have multiple collect methods? For example,
        #   `collect_from_enumeration_training_data`, `collect_from_custom_structures`,
        #   etc.? Or is it better to have a single `collect` method with multiple
        #   options?
        pass

    def map(self):
        # TODO:
        # For each StructureRecord in self.structures,
        # map the structure and populate StructureRecord.mappings with the results,
        # select the best mapping, and set the selected mapping index.
        #
        # Additional:
        # - Create a mapping_report.json output? Could hold summary information such
        #   as the number of structures that map to the same configuration, number of
        #   unique configurations, etc.
        pass

    def merge(self):
        # TODO
        pass

    def __repr__(self):
        from libcasm.xtal import pretty_json

        s = "StructureImportData:\n"
        s += f"- id: {self.id}\n"

        if self.meta is not None and "desc" in self.meta:
            s += f'- desc: {pretty_json(self.meta["desc"]).strip()}\n'

        n_structures = len(self.structures)
        n_mapped = sum(
            [
                1
                for structure in self.structures
                if structure.mapped_structure is not None
            ]
        )
        s += f"- enum_id: {self.enum_id}\n"
        s += f"- n_structures: {n_structures}\n"
        s += f"- n_mapped: {n_mapped}\n"
        s += f"- n_not_mapped: {n_structures - n_mapped}\n"

        # TODO:
        # - Number of structures that map to the same configuration?
        # - Number of unique configurations?
        # - Other info? Maybe `map` should create a mapping_report.json that could
        #   store this information and be read and used here.
        return s.strip()
