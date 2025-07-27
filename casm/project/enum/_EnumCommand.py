from typing import TYPE_CHECKING

from ._EnumData import EnumData

if TYPE_CHECKING:
    from casm.project import Project


class EnumCommand:
    """Methods to enumerate supercells, configurations, events, etc."""

    def __init__(self, proj: "Project"):
        self.proj = proj
        """casm.project.Project: CASM project."""

        self.last = None
        """Optional[casm.project.enum.EnumData]: Data from the last enumeration 
        operation."""

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
        enum: casm.project.enum.EnumData
            The enumeration data
        """
        return EnumData(proj=self.proj, id=id)

    def remove(self, id: str):
        """Remove enumeration data

        .. attention::

            This also permanently removes calculation directories!

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
