import pathlib
from typing import TYPE_CHECKING, Any, Union

from casm.project.enum import ConfigSelection

if TYPE_CHECKING:
    from casm.project import Project


class CalcData:
    """Data structure for calculation settings data in a CASM project

    The `calculation_settings` directory is a standard location for storing calculation
    settings for a particular calculation type inside a CASM project directory:

    .. code-block:: none

        <project>/
        └── calculation_settings/
            └── calctype.<calctype_id>/
                ├── calc.json
                ├── INCAR
                ├── KPOINTS
                └── other_calctype_files...



    """

    def __init__(self, proj: "Project", id: str):
        """

        .. rubric:: Constructor

        The CalcData object is constructed and all enumeration data is loaded. If the
        `scel_set.json` file does not exist, an empty SupercellSet is created. Other
        enumeration data is optional. To save any changes to the enumeration data, use
        the `commit` method.

        Parameters
        ----------
        proj: casm.project.Project
            The CASM project
        id: str
            The calculation type identifier. Calculation settings data is stored in the
            calculation settings directory at
            `<project>/calculation_settings/calctype.<id>/`.
        """

        self.proj = proj
        """casm.project.Project: CASM project"""

        self.id = id
        """str: Calculation type identifier"""

        settings_dir = self.proj.dir.calctype_settings_dir_v2(calctype=self.id)
        self.settings_dir = settings_dir
        """pathlib.Path: Calculation settings directory"""

        ### Data (load & commit) ###

        self.meta = dict()
        """dict: A description of the calculation type, read from `meta.json`."""

        # load data
        self.load()

    def load(self):
        """Read meta.json

        This will replace the current contents of this CalcData object with
        the contents of the associated files, or set the current contents to None if the
        associated files do not exist.
        """
        from casm.tools.shared.json_io import read_optional

        # read meta.json if it exists
        path = self.settings_dir / "meta.json"
        self.meta = read_optional(path, default=dict())

    def commit(self, verbose: bool = True):
        """Write meta.json

        If the data does not exist in this object, this will erase the associated
        files if they do exist.
        """
        from casm.tools.shared.json_io import safe_dump

        quiet = not verbose
        self.settings_dir.mkdir(parents=True, exist_ok=True)

        # write meta.json
        path = self.settings_dir / "meta.json"
        if len(self.meta) > 0:
            if not isinstance(self.meta, dict):
                raise TypeError(
                    "Error in CalcData.commit: CalcData.meta must be a dict"
                )
            safe_dump(
                data=self.meta,
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

    def __repr__(self):
        from libcasm.xtal import pretty_json

        s = "CalcData:\n"
        s += f"- id: {self.id}\n"

        if self.meta is not None and "desc" in self.meta:
            s += f'- desc: {pretty_json(self.meta["desc"]).strip()}\n'

        return s.strip()

    def list(self):
        """Print all files and directories in the calctype settings directory."""
        print(f"'{self.id}' settings files:")
        for name in self.listdir():
            print("- " + name)

    def listdir(self):
        """List files and directories in the calctype settings directory.

        Returns
        -------
        names: list[str]
            A list of file and directory names in the calctype settings directory.
        """
        return [f.name for f in self.settings_dir.iterdir()]

    def add_file(
        self,
        file: Union[str, pathlib.Path],
    ):
        """Add a file to the calctype settings directory (as a copy).

        Parameters
        ----------
        file: typing.Union[str, pathlib.Path]
            The path to the file to add. This file will be copied to the calctype
            settings directory.
        """
        import shutil

        path = pathlib.Path(file)

        if not path.exists():
            raise FileNotFoundError(f"File {path} does not exist.")
        if not path.is_file():
            raise ValueError(f"Path {path} is not a file.")

        dest_path = self.settings_dir / path.name
        shutil.copy2(src=path, dst=dest_path)

    def write_text_file(
        self,
        name: str,
        text: str,
    ):
        """Write a text file to the calctype settings directory.

        Parameters
        ----------
        name: str
            The name of the file to write.
        text: str
            The text to write to the file.
        """
        from casm.tools.shared.text_io import safe_write

        safe_write(text=text, path=self.settings_dir / name, force=True)

    def read_text_file(
        self,
        name: str,
    ) -> str:
        """Load a text file from the calctype settings directory.

        Parameters
        ----------
        name: str
            The name of the file to load.

        Returns
        -------
        text: str
            The text loaded from the file.
        """
        with open(self.settings_dir / name, "r") as file:
            return file.read()

    def write_json_file(
        self,
        name: str,
        data: dict,
    ):
        """Write a JSON file to the calctype settings directory.

        Parameters
        ----------
        name: str
            The name of the file to write.
        data: Any
            The data to write to the JSON file.
        """
        from casm.tools.shared.json_io import safe_dump

        safe_dump(data=data, path=self.settings_dir / name, force=True)

    def read_json_file(
        self,
        name: str,
    ) -> dict:
        """Load a JSON file from the calctype settings directory.

        Parameters
        ----------
        name: str
            The name of the file to load.

        Returns
        -------
        data: dict
            The data loaded from the JSON file.
        """
        from casm.tools.shared.json_io import read_required

        return read_required(path=self.settings_dir / name)

    def setup(
        self,
        config_selection: ConfigSelection,
        tool: Union[str, Any],
        use_run_dirs: bool = True,
    ):
        """Setup calculations for a selection of Configurations in an enumeration.

        Notes
        -----
        Configurations which have a `calc_status` other than "none" will be skipped
        and a warning will be printed. This is to avoid overwriting existing
        calculation files.

        Parameters
        ----------
        config_selection: ConfigSelection
            A selection of Configurations to set up calculations for. All selected
            configurations will have input files created.
        tool: Union[str, Any]
            A tool used to set up calculations. This may be a string identifier for a
            builtin calculation tool using the default construction parameters or a
            custom tool. Currently, the only builtin tool is:

            - "vasp": VASP calculation setup using
              :class:`~casm.tools.shared.ase_utils.AseVaspTool`

            If not a string, expected to be an
            object with a `setup` method with signature:

            .. code-block:: python

                ToolType.setup(
                    self,
                    casm_structure: libcasm.xtal.Structure,
                    calc_dir: pathlib.Path,
                    config: typing.Optional[libcasm.configuration.Configuration] = None,
                ):
                    ... write calculation input files ...

        use_run_dirs: bool = True
            If True, a subdirectory named `run.0` will be created in each configuration
            calculation directory and the input files will be written to that
            subdirectory. If False, the input files will be written directly to the
            configuration's calculation directory.
        """
        from casm.tools.shared.json_io import safe_dump

        quiet = True

        if isinstance(tool, str):
            from casm.tools.shared.ase_utils import AseVaspTool

            if tool == "vasp":
                tool = AseVaspTool(
                    calctype_settings_dir=self.settings_dir,
                )
            else:
                raise ValueError(f"Unknown tool: {tool}")

        n_jobs_not_ready = 0

        for record in config_selection:
            if not record.is_selected:
                continue

            if record.calc_status != "none":
                n_jobs_not_ready += 1
                print(f"skipping: {record.name} (status={record.calc_status})")
                continue

            calc_dir = record.calc_dir
            if use_run_dirs:
                # Write input to `run.0` subdirectory
                input_file_dir = calc_dir / "run.0"
            else:
                # Write input to the calculation directory directly
                input_file_dir = calc_dir
            casm_structure = record.configuration.to_structure()

            tool.setup(
                casm_structure=casm_structure,
                calc_dir=input_file_dir,
            )

            # Write status.json file
            safe_dump(
                data={"status": "setup"},
                path=calc_dir / "status.json",
                force=True,
                quiet=quiet,
            )

            # Write structure.json file
            safe_dump(
                data=casm_structure.to_dict(),
                path=calc_dir / "structure.json",
                force=True,
                quiet=quiet,
            )

            # Write configuration.json file
            safe_dump(
                data=record.configuration.to_dict(),
                path=calc_dir / "config.json",
                force=True,
                quiet=quiet,
            )

        if n_jobs_not_ready:
            print()
            print(
                f"Warning: {n_jobs_not_ready} jobs have status != 'none', "
                "so they were not setup."
            )
            print()
