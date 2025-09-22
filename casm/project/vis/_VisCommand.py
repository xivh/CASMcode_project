from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from casm.project import Project


class VisCommand:
    """Visualizations"""

    def __init__(self, proj: "Project"):

        import casm.vis
        import casm.vis.client as client

        self.proj = proj
        """casm.project.Project: CASM project."""

        config = casm.vis.get_config()

        self._api_url = config["CASMVIS_API_SERVER"]
        """str: The casm-vis API server URL."""

        self._vis_url = config["CASMVIS_SERVER"]
        """str: The casm-vis server URL."""

        try:
            casm.vis.start()
            result = client.project_add(project_path=self.proj.path)
            _proj_id = result["id"]
        except Exception:
            _proj_id = None
        self._proj_id = _proj_id
        """Optional[str]: Project id string in casm-vis."""

    def start(self):
        """Start casm-vis servers if not already running."""
        import casm.vis

        casm.vis.start()

    def stop(self):
        """Stop casm-vis servers if running."""
        import casm.vis

        casm.vis.stop()

    def enum(self, enum_id: str, view_id: str = "configuration_set"):
        """Visualize an enumeration in casm-vis

        Parameters
        ----------
        enum_id : str
            The enumeration identifier
        view_id : str = "configuration_set"
            One of:

            - "configuration_set": To display configurations in the enumeration's
              :py:attr:`~casm.project.enum.EnumData.configuration_set`.
            - "configuration_list": To display configurations in the enumeration's
              :py:attr:`~casm.project.enum.EnumData.configuration_list`.

        Returns
        -------
        id : str
            The new identifier string
        """
        import webbrowser

        if self._proj_id is None:
            raise RuntimeError(
                "Error: could not add project to casm-vis. "
                "Is the casm-vis API server running?"
            )
        enum = self.proj.enum.get(id=enum_id)
        if not enum.enum_dir.exists():
            raise FileNotFoundError(f"Enumeration '{enum_id}' does not exist.")
        url = f"{self._vis_url}/#/project/{self._proj_id}/enum/vis/"
        url += f"?enum_id={enum_id}&view_id={view_id}"
        webbrowser.open(url=url, new=2)
