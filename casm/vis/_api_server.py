import argparse
import copy
import os
import pathlib
from typing import Annotated, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, model_validator

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


# --- Pydantic models ---


class FilesRequest(BaseModel):
    path: Optional[str] = None


class FileItem(BaseModel):
    path: str
    is_dir: bool


class ProjectAddRequest(BaseModel):
    project_path: str
    id: Optional[str] = None


class ProjectInfo(BaseModel):
    id: str
    project_path: str
    generic_dof: list[str]
    prim_str: str


class ProjectRemoveRequest(BaseModel):
    project_path: Optional[str] = None
    id: Optional[str] = None

    @model_validator(mode="after")
    def check_exactly_one(self):
        has_path = self.project_path is not None
        has_id = self.id is not None
        if has_path and has_id:
            raise ValueError("Provide only one of 'project_path' or 'id'.")
        if not has_path and not has_id:
            raise ValueError("One of 'project_path' or 'id' is required.")
        return self


class MessageResponse(BaseModel):
    message: str


class ObjectId(BaseModel):
    id: str


# --- Helper functions ---


def get_project_ids():
    """Get the project IDs from the project_list.json file."""
    from casm.tools.shared.json_io import read_optional

    project_list_path = root / "project_list.json"
    default_list = list()
    data = read_optional(path=project_list_path, default=default_list)
    return [item["id"] for item in data]


def add_project(
    path: pathlib.Path,
    id: Optional[str] = None,
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


def remove_project_by_id(proj_id: str) -> MessageResponse:
    from casm.tools.shared.json_io import read_optional, safe_dump

    # Remove from project_list.json
    project_list_path = root / "project_list.json"
    default_list = list()
    project_list = read_optional(path=project_list_path, default=default_list)

    for item in project_list:
        if item["id"] == proj_id:
            break
    else:  # not found
        return MessageResponse(message=f"No project with id={proj_id} currently added.")

    project_list = [item for item in project_list if item["id"] != proj_id]
    safe_dump(project_list, path=project_list_path, force=True)

    # Remove from starred.json
    starred_path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=starred_path, default=default_data)
    if "projects" in data:
        data["projects"] = [id for id in data["projects"] if id != proj_id]
    safe_dump(data, path=starred_path, force=True)
    return MessageResponse(message=f"Project '{proj_id}' removed successfully.")


def remove_project_by_path(project_path_str: str) -> MessageResponse:
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
        return MessageResponse(
            message=f"No project at '{project_path_str}' currently added."
        )

    return remove_project_by_id(proj_id)


# --- Routes ---


@app.get("/casm/")
def home():
    return HTMLResponse(content=home_html)


@app.post("/files/", response_model=list[FileItem])
async def files_post(body: FilesRequest):
    """Get the files in a directory."""
    top = pathlib.Path(os.environ["HOME"]).resolve()
    path = pathlib.Path(body.path if body.path is not None else top).resolve()

    if path != top and not is_subdirectory(path, top):
        raise HTTPException(
            status_code=400,
            detail=f"Provided `path` '{path}' is not allowed.",
        )

    possible_parent = []
    if path != top:
        possible_parent.append(FileItem(path=str(path / ".."), is_dir=True))

    if not path.is_dir():
        raise HTTPException(
            status_code=400,
            detail="Provided `path` is not a directory.",
        )
    return possible_parent + [
        FileItem(path=str(path / child), is_dir=child.is_dir())
        for child in path.iterdir()
        if not child.name.startswith(".")
    ]


# Add projects:
@app.put("/casm/project/add/", response_model=ProjectInfo)
async def project_add(body: ProjectAddRequest):
    """Add a project to the project list."""
    from casm.project import project_path as get_project_path

    start = pathlib.Path(body.project_path)
    project_path = get_project_path(start=start)
    if project_path != start:
        raise HTTPException(
            status_code=422,
            detail=f"No project found at '{start}'. "
            "Must be exactly the project root directory.",
        )

    try:
        data = add_project(path=project_path, id=body.id)
        return data
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# Remove projects (from project_list.json only - do not delete files):
@app.put("/casm/project/{proj_id}/remove/", response_model=MessageResponse)
def project_remove(proj_id: str):
    """Remove a project from the project list.

    **Path parameter:**

    - **proj_id**: The ID of the project to remove.
    """
    from casm.tools.shared.json_io import read_optional, safe_dump

    project_ids = get_project_ids()
    if proj_id not in project_ids:
        raise HTTPException(
            status_code=422,
            detail=f"Project id='{proj_id}' not found.",
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
    return MessageResponse(message=f"Project '{proj_id}' removed successfully.")


# Remove projects (from project_list.json only - do not delete files):
@app.put("/casm/project/remove/", response_model=MessageResponse)
async def project_remove_alt(body: ProjectRemoveRequest):
    """Remove a project from the project list by path or ID.

    **Request body (JSON):** Provide exactly one of:

    - **project_path**: Path of the project to remove.
    - **id**: ID of the project to remove.
    """
    if body.project_path is not None:
        return remove_project_by_path(body.project_path)
    else:
        return remove_project_by_id(body.id)


@app.get("/casm/project/")
def project_get(project_path: str):
    """Get project settings.

    **Query parameter:**

    - **project_path**: Path to the project directory.
    """
    from casm.project import (
        DirectoryStructure,
    )
    from casm.project import project_path as get_project_path
    from casm.tools.shared.json_io import read_required

    start = pathlib.Path(project_path)
    resolved_path = get_project_path(start=start)
    if resolved_path != start:
        raise HTTPException(
            status_code=422,
            detail=f"No project found at '{start}'. "
            "Must be exactly the project directory root.",
        )

    dir = DirectoryStructure(start)
    try:
        return read_required(dir.project_settings())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=f"Project settings could not be read from '{resolved_path}'.",
        )


@app.get("/casm/project/list/", response_model=list[ProjectInfo])
def project_list_get():
    """Get the list of added projects."""
    from casm.tools.shared.json_io import read_optional

    # read ~/.casmvis/project_list.json:
    project_list_path = root / "project_list.json"
    default_list = list()
    return read_optional(path=project_list_path, default=default_list)


@app.get("/casm/project/starred/", response_model=list[str])
def project_starred_get():
    """Get the list of starred project IDs."""
    from casm.tools.shared.json_io import read_optional

    # read root/starred.json:
    path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=path, default=default_data)
    starred = data.get("projects", list())
    return starred


# Put starred projects:
@app.put("/casm/project/starred/", response_model=MessageResponse)
async def project_starred_put(body: Annotated[list[str], Body()]):
    """Update the starred projects.

    **Request body (JSON):** A list of project ID strings representing all starred projects.
    """
    from casm.tools.shared.json_io import read_optional, safe_dump

    # Validate the input:
    project_ids = get_project_ids()
    for project_id in body:
        if project_id not in project_ids:
            raise HTTPException(
                status_code=422,
                detail=f"id='{project_id}' not found.",
            )

    # Update root/starred.json:
    path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=path, default=default_data)
    data["projects"] = copy.deepcopy(body)
    safe_dump(data, path=path, force=True)

    return MessageResponse(message="Starred projects updated successfully.")


@app.get("/casm/project/{proj_id}/{obj_type}/list/", response_model=list[ObjectId])
def project_enum_list_get(proj_id: str, obj_type: str):
    """Get the list of IDs for a type of project object.

    **Path parameters:**

    - **proj_id**: The project ID.
    - **obj_type**: Object type — `"enum"` or `"bset"`.
    """
    proj = cache.get_project(proj_id)
    if obj_type == "enum":
        data = [ObjectId(id=id) for id in proj.enum.all()]
    elif obj_type == "bset":
        data = [ObjectId(id=id) for id in proj.bset.all()]
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
