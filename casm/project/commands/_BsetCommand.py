from typing import Optional

from casm.project import BsetData, Project


class BsetCommand:
    """Methods to construct and print cluster expansion basis sets"""

    def __init__(self, proj: Project):
        self.proj = proj
        """Project: CASM project."""

        self.last = None
        """Optional[BsetData]: Data from the last basis set operation."""

    def _check_bset(
        self,
        bset: Optional[str] = None,
    ):
        if bset is None:
            if self.proj.settings.default_clex is None:
                raise Exception(
                    "No default clex found in project. One of bset, clex is required."
                )
            bset = self.proj.settings.default_clex.bset
        return bset

    def all(self):
        """Return the identifiers of all basis sets

        Returns
        -------
        all_bset: list[str]
            A list of basis set identifiers
        """
        return self.proj.dir.all_bset()

    def list(self):
        """Print all basis sets"""
        for id in self.all():
            bset = self.get(id)
            print(bset)

    def get(self, id: str):
        """Load basis set data

        Parameters
        ----------
        id : str
            The basis set identifier

        Returns
        -------
        bset: BsetData
            The enumeration data
        """
        return BsetData(proj=self.proj, id=id)

    def remove(self, id: str):
        """Remove basis set data

        Parameters
        ----------
        id : str
            The basis set identifier
        """
        import shutil

        bset_dir = self.proj.dir.bset_dir(id)
        if not bset_dir.exists():
            raise FileNotFoundError(f"Basis set {id} does not exist.")
        shutil.rmtree(self.proj.dir.bset_dir(id))

    def copy(self, src_id: str, dest_id: str):
        """Copy basis set data

        Parameters
        ----------
        src_id : str
            The source basis set identifier
        dest_id : str
            The destination basis set identifier
        """
        data = self.get(src_id)
        data.id = dest_id

        bset_dir = self.proj.dir.bset_dir(dest_id)
        bset_dir.mkdir(parents=True, exist_ok=False)
        data.bset_dir = bset_dir
        data.commit()
