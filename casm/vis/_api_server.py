import argparse
import copy
import os
import pathlib
import typing

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from ._functions import get_config
from ._ServerCache import ServerCache

# Get paths:
this_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
assets_dir = this_dir / "assets"
logo_path = assets_dir / "logo.svg"
root = pathlib.Path(os.environ["HOME"]) / ".casmvis"
cache = ServerCache()

home_html = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>CASM</title>
    <link rel="stylesheet" href="https://use.typekit.net/tlb5xuy.css"/>
    <link rel="stylesheet" href="/static/css/style.css">
  </head>
  <body>
      <div><img src="/static/images/logo.svg" alt="CASM logo", width="200"></div>
  </body>
</html>
"""  # noqa: E501


app = FastAPI()
config = get_config()
casmvis_server = config["CASMVIS_SERVER"]

allowed_origins = [
    casmvis_server,  # casmvis
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# http codes:

# Success:
http_success = 200

# i.e. wrong parameters or types
http_bad_request = 400

# (unprocessable entity) i.e. parameters are correct type but invalid value
http_bad_logic = 422


def get_project_ids():
    """Get the project IDs from the project_list.json file.

    Returns
    -------
    project_ids: list[str]
        A list of project IDs.

    """
    from casm.tools.shared.json_io import read_optional

    project_list_path = root / "project_list.json"
    default_list = list()
    data = read_optional(path=project_list_path, default=default_list)
    return [item["id"] for item in data]


def add_project(
    path: pathlib.Path,
    id: typing.Optional[str] = None,
):
    """Add a project to the project list.

    Parameters
    ----------
    path : pathlib.Path
        The path to the project directory.
    id : Optional[str]
        An ID string used to refer to the project in menus, lists, etc. If None, the
        project name will be used. If `id` is already taken by another project, an
        index will be appended (i.e. "SiGe" -> "SiGe-1") or updated if already present
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
    Exception
        If no project is found at `path`, or if a project with the same path but
        different ID already exists.
    """
    import casm.project
    import libcasm.xtal as xtal
    from casm.tools.shared.json_io import read_optional, safe_dump

    start = path.resolve()

    project_path = casm.project.project_path(start=start)
    if project_path != start:
        raise Exception(
            f"No project found at '{start}'. "
            "Must be exactly the project directory root."
        )

    proj = casm.project.Project(path=project_path)
    project_list_path = root / "project_list.json"
    default_list = list()
    project_list = read_optional(path=project_list_path, default=default_list)

    data = {}
    data["project_path"] = str(project_path)
    data["generic_dof"] = proj.generic_dof_types
    data["prim_str"] = xtal.pretty_json(proj.prim.to_dict())

    # If a project with the same path exists, raise an exception if id is different:
    for item in project_list:
        if item["project_path"] == str(project_path):
            if id is None or item["id"] == id:
                # Project already added with the same ID or no ID was given:
                data["id"] = item["id"]
                return data

            else:
                # Project already added with different ID - error:

                raise Exception(
                    f"Project at path '{project_path}' "
                    f"is already added with id='{item['id']}'."
                )

    # If a new project, ensure the id is unique:
    if id is None:
        id = proj.name

    project_ids = get_project_ids()
    while id in project_ids:
        # If id ends in a "-<number>", increment the number until a unique id is found:
        if "-" in id:
            base, number = id.rsplit("-", 1)
            if number.isdigit():
                id = f"{base}-{int(number) + 1}"
            else:
                id = f"{id}-1"
        else:
            id = f"{id}-1"

    data["id"] = id

    project_list.append(data)

    safe_dump(project_list, path=project_list_path, force=True)
    return data


def is_subdirectory(path: pathlib.Path, top: pathlib.Path) -> bool:
    """Check if `top` is a parent of `path`.

    Parameters
    ----------
    path : pathlib.Path
        The path to check.
    top : pathlib.Path
        The top directory.

    Returns
    -------
    is_subdir: bool
        True if `top` is a parent of `path`, False otherwise.
    """
    # Resolve the absolute paths
    path = path.resolve()
    top = top.resolve()
    # Check if `top` is a parent of `path`
    return top in path.parents


@app.get("/casm/")
def home():
    return HTMLResponse(content=home_html)


@app.post("/files/")
async def files_post(request: Request):
    """Get the files in a directory.

    Expects to receive a JSON object with the following format:

    - path: Optional[str]
        The path to a directory. If not provided, defaults to the user's home directory.

    Returns
    -------
    list[dict]
        A list of dictionaries with the following keys:

        - path: str
            The path to the file or directory.
        - is_dir: bool
            True if the path is a directory, False otherwise.

    """
    in_data = await request.json()
    top = pathlib.Path(os.environ["HOME"]).resolve()
    path = pathlib.Path(in_data.get("path", top)).resolve()

    # Validate the path:
    # path must be a sub-directory (direct or indirect)
    # of os.environ["HOME"]:
    if path != top and not is_subdirectory(path, top):
        return JSONResponse(
            content={"error": f"Provided `path` '{path}' is not allowed."},
            status_code=400,
        )

    possible_parent = []
    if path != top:
        possible_parent.append({"path": str(path / ".."), "is_dir": True})

    if not path.is_dir():
        return JSONResponse(
            content={"error": "Provided `path` is not a directory."},
            status_code=http_bad_request,
        )
    return possible_parent + [
        {"path": str(path / child), "is_dir": child.is_dir()}
        for child in path.iterdir()
        if not child.name.startswith(".")
    ]


# Put starred projects:
@app.put("/casm/project/add/")
async def project_add(request: Request):
    """Add a project to the project list.

    Expects to receive a JSON object with the following format:

    - project_path: str
        The path to the project directory.
    - id: Optional[str]
        An ID string used to refer to the project in menus, lists, etc. If None, the
        project name will be used. Must be unique on this machine for the current user.

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

    """

    from casm.project import project_path as get_project_path

    in_data = await request.json()

    # Validate "project_path":
    if "project_path" not in in_data:
        return JSONResponse(
            content={"error": "No `project_path` parameter provided."},
            status_code=http_bad_request,
        )
    start = pathlib.Path(in_data["project_path"])
    project_path = get_project_path(start=start)
    if project_path != start:
        return JSONResponse(
            content={
                "error": f"No project found at '{start}'. "
                "Must be exactly the project root directory."
            },
            status_code=http_bad_logic,
        )

    # Validate "id":
    if "id" in in_data and not isinstance(in_data["id"], str):
        return JSONResponse(
            content={"error": "Optional `id` parameter must be a string if provided."},
            status_code=http_bad_request,
        )
    id = in_data.get("id", None)

    try:
        data = add_project(path=project_path, id=id)
        return data
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=http_bad_logic)


def remove_project_by_id(proj_id: str):
    from casm.tools.shared.json_io import read_optional, safe_dump

    # Remove from project_list.json
    project_list_path = root / "project_list.json"
    default_list = list()
    project_list = read_optional(path=project_list_path, default=default_list)

    for item in project_list:
        if item["id"] == proj_id:
            break
    else:  # not found
        return JSONResponse(
            content={"message": f"No project with id={proj_id} currently added."},
            status_code=http_success,
        )

    project_list = [item for item in project_list if item["id"] != proj_id]
    safe_dump(project_list, path=project_list_path, force=True)

    # Remove from starred.json
    starred_path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=starred_path, default=default_data)
    if "projects" in data:
        data["projects"] = [id for id in data["projects"] if id != proj_id]
    safe_dump(data, path=starred_path, force=True)
    return JSONResponse(
        content={"message": f"Project '{proj_id}' removed successfully."},
        status_code=http_success,
    )


def remove_project_by_path(project_path_str: str):
    from casm.tools.shared.json_io import read_optional

    project_list_path = root / "project_list.json"
    default_list = list()
    project_list = read_optional(path=project_list_path, default=default_list)

    proj_id = None
    for item in project_list:
        if item["project_path"] == project_path_str:
            proj_id = item["id"]
            break

    if proj_id is None:
        return JSONResponse(
            content={"message": f"No project at '{project_path_str}' currently added."},
            status_code=http_success,
        )

    return remove_project_by_id(proj_id)


# Remove projects (from project_list.json only - do not delete files):
@app.put("/casm/project/{proj_id}/remove/")
def project_remove(proj_id: str):
    """Remove a project from the project list.

    Parameters
    ----------
    proj_id : str
        The ID of the project to remove.

    Returns
    -------
    data: dict
        A dictionary containing either ``"error": str`` (if unsuccessful) or
        ``"message": str`` (if successful).

    """
    from casm.tools.shared.json_io import read_optional, safe_dump

    # Validate "id":
    if not isinstance(proj_id, str):
        return JSONResponse(
            content={"error": "Project ID must be a string."},
            status_code=http_bad_request,
        )

    project_ids = get_project_ids()
    if proj_id not in project_ids:
        return JSONResponse(
            content={"error": f"Project id='{proj_id}' not found."},
            status_code=http_bad_logic,
        )

    # Remove from project_list.json
    project_list_path = root / "project_list.json"
    default_list = list()
    project_list = read_optional(path=project_list_path, default=default_list)
    project_list = [item for item in project_list if item["id"] != proj_id]
    safe_dump(project_list, path=project_list_path, force=True)

    # Remove from starred.json
    starred_path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=starred_path, default=default_data)
    for key in list(data.keys()):
        if key == "projects":
            data[key] = [item for item in data[key] if item != proj_id]
        elif proj_id in data[key]:
            del data[key][proj_id]
    safe_dump(data, path=starred_path, force=True)
    return JSONResponse(
        content={"message": f"Project '{proj_id}' removed successfully."},
        status_code=http_success,
    )


# Remove projects (from project_list.json only - do not delete files):
@app.put("/casm/project/remove/")
async def project_remove_alt(request: Request):
    """Remove a project from the project list.

    Expects to receive a JSON object with the following format:

    - project_path: Optional[str]
        The path of the project to remove.
    - id: Optional[str]
        The ID of the project to remove.

    Returns
    -------
    data: dict
        A dictionary containing either ``"error": str`` (if unsuccessful) or
        ``"message": str`` (if successful).

    """

    in_data = await request.json()

    if "project_path" in in_data and "id" in in_data:
        return JSONResponse(
            content={"error": "Provide only one of 'project_path' or 'id'."},
            status_code=http_bad_request,
        )

    # Validate "project_path":
    if "project_path" in in_data:
        project_path_str = in_data["project_path"]
        if not isinstance(project_path_str, str):
            return JSONResponse(
                content={"error": "`project_path` must be a string."},
                status_code=http_bad_request,
            )
        return remove_project_by_path(project_path_str)
    elif "id" in in_data:
        proj_id = in_data["id"]
        if not isinstance(proj_id, str):
            return JSONResponse(
                content={"error": "`id` must be a string."},
                status_code=http_bad_request,
            )
        return remove_project_by_id(proj_id)
    else:
        return JSONResponse(
            content={"error": "One of 'project_path' or 'id' is required."},
            status_code=http_bad_request,
        )


@app.get("/casm/project/")
async def project_get(request: Request):
    from casm.project import (
        DirectoryStructure,
    )
    from casm.project import project_path as get_project_path
    from casm.tools.shared.json_io import read_required

    in_data = await request.json()
    if "project_path" not in in_data:
        return JSONResponse(
            content={"error": "No project name or path provided."},
            status_code=http_bad_request,
        )
    start = pathlib.Path(in_data["project_path"])
    project_path = get_project_path(start=start)
    if project_path != start:
        return JSONResponse(
            content={
                "error": f"No project found at '{start}'. "
                "Must be exactly the project directory root."
            },
            status_code=http_bad_logic,
        )

    dir = DirectoryStructure(start)
    try:
        return read_required(dir.project_settings())
    except Exception:
        return JSONResponse(
            content={
                "error": "Project settings could not be read from "
                f"'{project_path}'."
            },
            status_code=http_bad_logic,
        )


@app.get("/casm/project/list/")
def project_list_get():
    """Get the list of projects.

    Returns
    -------
    data: list[dict]
        A list of dictionaries with the following keys:

        - id: str
            The ID of the project.
        - project_path: str
            The path to the project directory.
        - generic_dof: list[str]
            The generic degrees of freedom on the prim, generic meaning any of
            "occ", "disp", "strain", or "magspin" (without strain or magspin flavor).
        - prim_str: str
            The JSON string representation of the project's prim.
    """
    from casm.tools.shared.json_io import read_optional

    # read ~/.casmvis/project_list.json:
    project_list_path = root / "project_list.json"
    default_list = list()
    return read_optional(path=project_list_path, default=default_list)


@app.get("/casm/project/starred/")
def project_starred_get():
    from casm.tools.shared.json_io import read_optional

    # read root/starred.json:
    path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=path, default=default_data)
    starred = data.get("projects", list())
    return starred


# Put starred projects:
@app.put("/casm/project/starred/")
async def project_starred_put(request: Request):
    """Update the starred projects.

    Expects to receive a JSON list of project ID str indicating all the starred
    projects.

    Returns
    -------
    data: dict
        A dictionary with the following keys

        - message: Optional[str]
            A message indicating the success of the operation.
        - error: Optional[str]
            An error message if the operation failed.
    """
    from casm.tools.shared.json_io import read_optional, safe_dump

    # Accepts a list of str (IDs of starred projects)

    # Get the data from the request:
    in_data = await request.json()
    if not isinstance(in_data, list):
        return JSONResponse(
            content={"error": "Data must be a list of project_id."},
            status_code=http_bad_request,
        )

    # Validate the input:
    project_ids = get_project_ids()
    for project_id in in_data:
        if not isinstance(project_id, str):
            return JSONResponse(
                content={"error": "`id` must be a string."},
                status_code=http_bad_request,
            )
        if project_id not in project_ids:
            return JSONResponse(
                content={"error": f"id='{project_id}' not found."},
                status_code=http_bad_logic,
            )

    # Update root/starred.json:
    path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=path, default=default_data)
    data["projects"] = copy.deepcopy(in_data)
    safe_dump(data, path=path, force=True)

    return JSONResponse(
        content={"message": "Starred projects updated successfully."},
        status_code=http_success,
    )


@app.get("/casm/project/{proj_id}/{obj_type}/list/")
def project_enum_list_get(proj_id: str, obj_type: str):
    """Get the list of IDs of some type of project objects (enum, bset, etc.)

    Parameters
    ----------
    proj_id : str
        The ID of the project.
    obj_type : str
        The type of object to list. Can be "enum" or "bset".

    Returns
    -------
    data : list[dict]
        A list of dictionaries with the following keys:
        - id: str
            The ID of the object.
    """
    proj = cache.get_project(proj_id)
    if obj_type == "enum":
        data = [{"id": id} for id in proj.enum.all()]
    elif obj_type == "bset":
        data = [{"id": id} for id in proj.bset.all()]
    else:
        data = []

    return data


def main():
    """Run the CASM API server."""

    # Use argparse to get `debug` and `port` from command line arguments, if they exist:
    parser = argparse.ArgumentParser(description="Run the CASM API server.")
    parser.add_argument(
        "--debug", action="store_true", default=False, help="Enable debug mode"
    )
    args = parser.parse_args()

    import threading

    import uvicorn

    url = config["CASMVIS_API_SERVER"]
    port = int(url.split(":")[-1])

    print(f"Starting CASM API server ({url})...")

    def run_app():
        uvicorn.run(
            app,
            host="localhost",
            port=port,
            log_level="debug" if args.debug else "info",
        )

    # Start the app in a separate thread
    thread = threading.Thread(target=run_app)
    thread.start()
