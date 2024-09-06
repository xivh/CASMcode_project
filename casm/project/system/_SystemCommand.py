from typing import TYPE_CHECKING

from ._SystemData import SystemData

if TYPE_CHECKING:
    from casm.project import Project


class SystemCommand:
    """Holds input files describing parameters for model systems used for Monte Carlo
    simulations or other predictions"""

    def __init__(self, proj: "Project"):
        self.proj = proj
        """casm.project.Project: CASM project."""

    def all(self):
        """Return the identifiers of all systems

        Returns
        -------
        all_system: list[str]
            A list of system identifiers
        """
        return self.proj.dir.all_system()

    def list(self):
        """Print all systems"""
        for id in self.all():
            system_data = self.get(id)
            print(system_data)

    def get(self, id: str):
        """Load system data

        Parameters
        ----------
        id : str
            The system identifier

        Returns
        -------
        system_data: SystemData
            The system data
        """
        return SystemData(proj=self.proj, id=id)

    def remove(self, id: str):
        """Remove system data

        Parameters
        ----------
        id : str
            The system identifier
        """
        import shutil

        system_dir = self.proj.dir.system_dir(id)
        if not system_dir.exists():
            raise FileNotFoundError(f"System {id} does not exist.")
        shutil.rmtree(self.proj.dir.system_dir(id))

    def copy(self, src_id: str, dest_id: str):
        """Copy system data

        Parameters
        ----------
        src_id : str
            The source system identifier
        dest_id : str
            The destination system identifier
        """
        data = self.get(src_id)
        data.id = dest_id

        system_dir = self.proj.dir.system_dir(dest_id)
        system_dir.mkdir(parents=True, exist_ok=False)
        data.system_dir = system_dir
        data.commit()
