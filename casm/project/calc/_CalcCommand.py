from typing import TYPE_CHECKING

from ._CalcData import CalcData

if TYPE_CHECKING:
    from casm.project import Project


class CalcCommand:
    """Calculation settings management"""

    def __init__(self, proj: "Project"):
        self.proj = proj

    def all(self):
        """Return the identifiers of all calculation types

        Returns
        -------
        all_calctype: list[str]
            A list of calculation identifiers
        """
        return self.proj.dir.all_calctype_v2()

    def list(self):
        """Print all calculation types"""
        for id in self.all():
            obj = self.get(id)
            print(obj)

    def get(self, id: str):
        """Load calculation settings data

        Parameters
        ----------
        id : str
            The calculation type identifier

        Returns
        -------
        calctype: casm.project.calc.CalcData
            The calculation settings data
        """
        return CalcData(proj=self.proj, id=id)

    def remove(self, id: str):
        """Remove calculation settings data

        .. attention::

            This only clears the calculation type settings directory, it does not
            remove the calculations directories found within enumeration directories,
            or any other data.

        Parameters
        ----------
        id : str
            The calculation type identifier
        """
        import shutil

        calctype_settings_dir = self.proj.dir.calctype_settings_dir_v2(calctype=id)
        if not calctype_settings_dir.exists():
            raise FileNotFoundError(f"Calculation type {id} does not exist.")
        shutil.rmtree(calctype_settings_dir)

    def copy(self, src_id: str, dest_id: str):
        """Copy calculation type settings data

        Parameters
        ----------
        src_id : str
            The source calculation type identifier
        dest_id : str
            The destination calculation type identifier
        """
        import shutil

        src_dir = self.proj.dir.calctype_settings_dir_v2(calctype=src_id)
        if not src_dir.exists():
            raise FileNotFoundError(f"Calculation type {src_id} does not exist.")
        dest_dir = self.proj.dir.calctype_settings_dir_v2(calctype=dest_id)
        shutil.copytree(src=src_dir, dst=dest_dir, dirs_exist_ok=True)
