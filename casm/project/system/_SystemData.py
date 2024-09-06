from typing import TYPE_CHECKING

from casm.project.json_io import read_optional, safe_dump

if TYPE_CHECKING:
    from casm.project import Project


class SystemData:
    """Data structure for model systems used for Monte Carlo simulations or other
    predictions

    The CASM project system directory structure:

    For a basic system with a single set of parameters, the system information
        is expected to be stored in a directory named `system.<id>`:

        .. code-block:: shell

            systems/
            └── system.<id>/
                ├── formation_energy_eci.json
                ├── system.json
                ...

    For statistics, related systems may be stored in subdirectories as:

    .. code-block:: shell

        systems/
        └── system.<id>/
            ├── 0/
            │   ├── formation_energy_eci.0.json
            │   ├── system.0.json
            │   ...
            ├── 1/
            │   ├── formation_energy_eci.1.json
            │   ├── system.1.json
            │   ...
            └── 2/
                ├── formation_energy_eci.2.json
                ├── system.2.json
                ...

    The `system.json` file contains the model system parameters used to construct
    a :class:`libcasm.clexmonte.System` instance. Other files such as cluster
    expansion coefficients, KMC event data and local cluster expansion coefficients,
    etc., may also be stored in the system directory.

    An optional `meta.json` file can be used to store a description of the enumeration
    and other custom information. If "desc" is found in `meta`, it will be printed by
    `print`.

    """

    def __init__(self, proj: "Project", id: str):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        proj: casm.project.Project
            The CASM project
        id: str
            The system identifier. System data is stored in the
            system directory at `<project>/systems/system.<id>/`.
        """

        self.proj = proj
        """Project: CASM project reference"""

        self.id = id
        """str: System identifier"""

        self.system_dir = self.proj.dir.system_dir(system=id)
        """pathlib.Path: System directory"""

        self.system_count = self.proj.dir.system_count(system=id)
        """pathlib.Path: For statistics, the number of sampled systems"""

        ### Data (load & commit) ###

        self.meta = dict()
        """dict: A description of the system, read from `meta.json`."""

        # load data
        self.load()

    def load(self):
        """Read meta.json

        This will replace the current contents of this SystemData object with
        the contents of the associated files, or set the current contents to None if the
        associated files do not exist.
        """

        # read meta.json if it exists
        path = self.system_dir / "meta.json"
        self.meta = read_optional(path, default=dict())

        # set system_count
        self.system_count = self.proj.dir.system_count(system=self.id)

    def commit(self, verbose: bool = True):
        """Write meta.json

        If the data does not exist in this object, this will erase the associated
        files if they do exist.
        """
        quiet = not verbose
        self.system_dir.mkdir(parents=True, exist_ok=True)

        # write meta.json
        path = self.system_dir / "meta.json"
        if len(self.meta) > 0:
            if not isinstance(self.meta, dict):
                raise TypeError(
                    "Error in SystemData.commit: SystemData.meta must be a dict"
                )
            safe_dump(
                data=self.meta,
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

    def clear(self):
        """Clear system data"""
        pass

    def __repr__(self):
        from libcasm.xtal import pretty_json

        s = "SystemData:\n"
        s += f"- id: {self.id}\n"

        if self.meta is not None and "desc" in self.meta:
            s += f'- desc: {pretty_json(self.meta["desc"]).strip()}\n'

        # TODO:
        # - Number sampled systems;
        return s.strip()
