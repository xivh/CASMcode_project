import pathlib
from typing import Optional, Union

import requests

from casm.vis import get_config

config = get_config()


def handle_response(response):

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"Error: {e}")
        if "error" in response.json():
            print(response.json()["error"])
        raise e
    return response.json()


def resolve(path: Union[str, pathlib.Path]) -> str:
    return str(pathlib.Path(path).resolve())


def project_add(
    project_path: Union[str, pathlib.Path],
    id: Optional[str] = None,
):
    """Add a CASM project to the casm-vis project list

    Parameters
    ----------
    project_path: Union[str, pathlib.Path]
        The path to the CASM project. Must be the project root directory.
    id: Optional[str], optional
        An ID string used to refer to the project. If None, the project name will be
        used. If `id` is already taken by another project, an index will be appended
        (i.e. "SiGe" -> "SiGe-1") or updated if already present
        (i.e. "SiGe-2" -> "SiGe-3").

    Returns
    -------
    data : dict
        A dictionary with the following keys:

        - id: str
            The ID of the project.
        - project_path: str
            The path to the project directory.
        - generic_dof: list[str]
            The generic degrees of freedom on the prim, generic meaning any of
            "occ", "disp", "strain", or "magspin" (without strain or magspin flavor).
        - prim_str: str
            The JSON string representation of the project's prim.

    Raises
    ------
    requests.HTTPError
        If the request to the casm-vis API server fails. Possible logic errors include:

        - Providing a `project_path` that does not exist or is not a CASM project.
        - Adding a project that is already added (same `project_path`) will raise an
          error if `id` is provided and it does not match the existing project's ID.
    """

    # @app.route("/casm/project/add/", methods=["PUT"])
    # data: {
    #     "project_path": str,
    #     "id": str,
    # }
    api_url = config["CASMVIS_API_SERVER"]

    url = f"{api_url}/casm/project/add/"
    data = {
        "project_path": resolve(project_path),
    }
    if id is not None:
        data["id"] = str(id)
    return handle_response(requests.put(url, json=data))


def project_remove(
    project_path: Optional[Union[str, pathlib.Path]] = None,
    id: Optional[str] = None,
):
    """Remove a CASM project from the casm-vis project list

    One and only one of `project_path` or `id` must be provided.

    Parameters
    ----------
    project_path: Optional[Union[str, pathlib.Path]] = None
        The path to the CASM project. Must be the project root directory.
    id: Optional[str] = None
        The ID string used to refer to the project.

    Returns
    -------
    data: dict
        A dictionary containing either ``"error": str`` (if unsuccessful) or
        ``"message": str`` (if successful).

    Raises
    ------
    requests.HTTPError
        If the request to the casm-vis API server fails. Possible logic errors include:

        - Providing an `id` that does not exist in the project list.

    ValueError
        If neither or both of `project_path` and `id` are provided.
    """

    # @app.route("/casm/project/<proj_id>/remove/", methods=["PUT"])
    api_url = config["CASMVIS_API_SERVER"]
    url = f"{api_url}/casm/project/remove/"
    data = dict()
    if project_path is not None and id is not None:
        raise ValueError("Error: must provide only one of 'project_path' or 'id'")
    if project_path is None and id is None:
        raise ValueError("Error: must provide only one of 'project_path' or 'id'")
    if project_path is not None:
        data["project_path"] = resolve(project_path)
    if id is not None:
        data["id"] = str(id)

    return handle_response(requests.put(url, json=data))
