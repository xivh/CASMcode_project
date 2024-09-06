from typing import TYPE_CHECKING, Optional

from ._StructureImportData import StructureImportData

if TYPE_CHECKING:
    from casm.project import Project


class StructureImportCommand:
    """Methods to import calculated structures as configurations with properties"""

    def __init__(self, proj: "Project"):
        self.proj = proj
        """casm.project.Project: CASM project."""

    def all(self):
        """Return the identifiers of all structure imports

        Returns
        -------
        all_import: list[str]
            A list of structure import identifiers
        """
        return self.proj.dir.all_import()

    def list(self):
        """Print all structure imports"""
        for id in self.all():
            structure_import = self.get(id)
            print(structure_import)

    def get(self, id: str, enum_id: Optional[str] = None):
        """Load structure import data

        Parameters
        ----------
        id : str
            The structure import identifier
        enum_id: Optional[str] = None
            An enumeration identifier. Mapped supercells and configurations are stored
            in the enumeration directory at `<project>/enumerations/enum.<enum_id>/`.
            The first time `StructureImportData` is constructed, an `enum_id` is
            required. Once the `StructureImportData` is saved with a `commit`, then the
            `enum_id` is stored in `settings.json`. On subsequent constructions, the
            `enum_id` will be read from `settings.json` and is not needed by the
            constructor.

        Returns
        -------
        structure_import: StructureImportData
            The structure import data
        """
        return StructureImportData(proj=self.proj, id=id, enum_id=enum_id)

    def remove(self, id: str):
        """Remove structure import data

        Parameters
        ----------
        id : str
            The structure import identifier
        """
        import shutil

        import_dir = self.proj.dir.import_dir(id)
        if not import_dir.exists():
            raise FileNotFoundError(f"Import {id} does not exist.")
        shutil.rmtree(self.proj.dir.import_dir(id))

    def copy(self, src_id: str, dest_id: str):
        """Copy structure import data

        Parameters
        ----------
        src_id : str
            The source structure import identifier
        dest_id : str
            The destination structure import identifier
        """
        data = self.get(src_id)
        data.id = dest_id

        import_dir = self.proj.dir.import_dir(dest_id)
        import_dir.mkdir(parents=True, exist_ok=False)
        data.import_dir = import_dir
        data.commit()
