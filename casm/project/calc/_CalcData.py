from typing import TYPE_CHECKING

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

        calctype_settings_dir = self.proj.dir.calctype_settings_dir_v2(calctype=self.id)
        self.calctype_settings_dir = calctype_settings_dir
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
        path = self.calctype_settings_dir / "meta.json"
        self.meta = read_optional(path, default=dict())

    def commit(self, verbose: bool = True):
        """Write meta.json

        If the data does not exist in this object, this will erase the associated
        files if they do exist.
        """
        from casm.tools.shared.json_io import safe_dump

        quiet = not verbose
        self.calctype_settings_dir.mkdir(parents=True, exist_ok=True)

        # write meta.json
        path = self.calctype_settings_dir / "meta.json"
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
        """List files and directories in the calctype settings directory.

        Returns
        -------
        names: list[str]
            A list of file and directory names in the calctype settings directory.
        """
        return [f.name for f in self.calctype_settings_dir.iterdir()]

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

        safe_write(text=text, path=self.calctype_settings_dir / name, force=True)

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
        with open(self.calctype_settings_dir / name, "r") as file:
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

        safe_dump(data=data, path=self.calctype_settings_dir / name, force=True)

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

        return read_required(path=self.calctype_settings_dir / name)
