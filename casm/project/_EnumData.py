from typing import Optional, TypeVar

from casm.project._Project import Project
from casm.project.json_io import (
    read_optional,
    safe_dump,
)
from libcasm.configuration import (
    ConfigurationSet,
    SupercellSet,
)

EnumDataType = TypeVar("EnumDataType", bound="EnumData")


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

    def merge(self, src_data: EnumDataType):
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
