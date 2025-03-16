import os
import pathlib
from typing import Any

import casm.project
from casm.project.json_io import read_optional

root = pathlib.Path(os.environ["HOME"]) / ".casmvis"


class ServerCache:
    def __init__(self):
        self.project: dict[str, casm.project.Project] = dict()
        """dict[str, casm.project.Project]: Cache for CASM projects"""

        self.app: dict[tuple, Any] = dict()
        """dict: Cache for objects used to serve Bokeh applications.
        
        The app cache is a dictionary with keys of type tuple, where the 
        first element of the tuple should be the bokeh app path and the remaining 
        element are determined by the bokeh app.
        
        """

    def get_project(self, project_id: str) -> casm.project.Project:
        """Get a project, by casmvis ID, constructing if necessary.

        Parameters
        ----------
        project_id: str
            The project ID.

        Returns
        -------
        project: casm.project.Project
            The project.

        """
        if project_id in self.project:
            return self.project[project_id]

        project_list_path = root / "project_list.json"
        default_list = list()
        data = read_optional(path=project_list_path, default=default_list)

        project_path = None
        for item in data:
            if item["id"] == project_id:
                project_path = item["project_path"]
                break

        if project_path is None:
            raise Exception(f"Project {project_id} not found in project list.")

        try:
            self.project[project_id] = casm.project.Project(path=project_path)
        except Exception as e:
            raise Exception(
                f"Error loading project {project_id} from path {project_path}: {e}"
            )

        return self.project[project_id]
