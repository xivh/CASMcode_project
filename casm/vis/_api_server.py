import argparse
import copy
import os
import pathlib
import typing

from flask import (
    Flask,
    jsonify,
    render_template_string,
    request,
)
from flask_cors import CORS

from casm.project.plot import ServerCache
from casm.vis import get_config

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
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
  </head>
  <body>
      <div><img src="{{ url_for('static', filename='images/logo.svg') }}" alt="CASM logo", width="200"></div>
  </body>
</html>
"""  # noqa: E501


app = Flask(__name__)
config = get_config()
casmvis_server = config["CASMVIS_SERVER"]

allowed_origins = [
    casmvis_server,  # casmvis
]
CORS(
    app,
    resources={
        r"/casm*": {"origins": allowed_origins},
        r"/files*": {"origins": allowed_origins},
    },
)


def get_project_ids():
    """Get the project IDs from the project_list.json file.

    Returns
    -------
    project_ids: list[str]
        A list of project IDs.

    """
    from casm.project.json_io import read_optional

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
    import casm.project
    import libcasm.xtal as xtal
    from casm.project.json_io import read_optional, safe_dump

    start = path.resolve()

    project_path = casm.project.project_path(start=start)
    if project_path != start:
        raise Exception(
            f"No project found at '{start}'. "
            "Must be exactly the project directory root."
        )

    proj = casm.project.Project(path=project_path)
    if id is None:
        id = proj.name

    project_list_path = root / "project_list.json"
    default_list = list()
    project_list = read_optional(path=project_list_path, default=default_list)

    # If a project with the same path exists, raise an exception:
    for item in project_list:
        if item["project_path"] == str(project_path):
            raise Exception(
                f"Project at path '{project_path}' "
                f"is already added with ID={item['id']}."
            )

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

    data = {}
    data["id"] = id
    data["project_path"] = str(project_path)
    data["generic_dof"] = proj.generic_dof_types
    data["prim_str"] = xtal.pretty_json(proj.prim.to_dict())

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


@app.route("/casm/")
def home():
    return render_template_string(home_html)


@app.route("/files/", methods=["POST"])
def files_post():
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
    in_data = request.get_json()
    top = pathlib.Path(os.environ["HOME"]).resolve()
    path = pathlib.Path(in_data.get("path", top)).resolve()

    # Validate the path:
    # path must be a sub-directory (direct or indirect)
    # of os.environ["HOME"]:
    if path != top and not is_subdirectory(path, top):
        return jsonify({"error": f"Provided `path` '{path}' is not allowed."}), 400

    possible_parent = []
    if path != top:
        possible_parent.append({"path": str(path / ".."), "is_dir": True})

    if not path.is_dir():
        return jsonify({"error": "Provided `path` is not a directory."}), 400
    return jsonify(
        possible_parent
        + [
            {"path": str(path / child), "is_dir": child.is_dir()}
            for child in path.iterdir()
            if not child.name.startswith(".")
        ]
    )


# Put starred projects:
@app.route("/casm/project/add/", methods=["PUT"])
def project_add():
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

    in_data = request.get_json()
    if "project_path" not in in_data:
        return jsonify({"error": "No `project_path` parameter provided."}), 400
    start = pathlib.Path(in_data["project_path"])
    project_path = get_project_path(start=start)
    if project_path != start:
        return (
            jsonify(
                {
                    "error": f"No project found at '{start}'. "
                    "Must be exactly the project directory root."
                }
            ),
            400,
        )

    if "id" in in_data and not isinstance(in_data["id"], str):
        return (
            jsonify({"error": "Optional `id` parameter must be a string if provided."}),
            400,
        )
    id = in_data.get("id", None)

    try:
        data = add_project(path=project_path, id=id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Remove projects (from project_list.json only - do not delete files):
@app.route("/casm/project/<proj_id>/remove/", methods=["PUT"])
def project_remove(proj_id):
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
    from casm.project.json_io import read_optional, safe_dump

    if not isinstance(proj_id, str):
        return jsonify({"error": "Project ID must be a string."}), 400

    project_ids = get_project_ids()
    if proj_id not in project_ids:
        return jsonify({"error": f"Project ID '{proj_id}' not found."}), 400

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
    return jsonify({"message": f"Project '{proj_id}' removed successfully."}), 200


@app.route("/casm/project/")
def project_get():
    from casm.project import (
        DirectoryStructure,
    )
    from casm.project import project_path as get_project_path
    from casm.project.json_io import read_required

    in_data = request.get_json()
    if "project_path" not in in_data:
        return jsonify({"error": "No project name or path provided."}), 400
    start = pathlib.Path(in_data["project_path"])
    project_path = get_project_path(start=start)
    if project_path != start:
        return (
            jsonify(
                {
                    "error": f"No project found at '{start}'. "
                    "Must be exactly the project directory root."
                }
            ),
            400,
        )

    dir = DirectoryStructure(start)
    try:
        return jsonify(read_required(dir.project_settings()))
    except Exception:
        return (
            jsonify(
                {
                    "error": "Project settings could not be read from "
                    f"'{project_path}'."
                }
            ),
            400,
        )


@app.route("/casm/project/list/")
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
    from casm.project.json_io import read_optional

    # read ~/.casmvis/project_list.json:
    project_list_path = root / "project_list.json"
    default_list = list()
    return jsonify(read_optional(path=project_list_path, default=default_list))


@app.route("/casm/project/starred/")
def project_starred_get():
    from casm.project.json_io import read_optional

    # read root/starred.json:
    path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=path, default=default_data)
    starred = data.get("projects", list())
    return jsonify(starred)


# Put starred projects:
@app.route("/casm/project/starred/", methods=["PUT"])
def project_starred_put():
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
    from casm.project.json_io import read_optional, safe_dump

    # Accepts a list of str (IDs of starred projects)

    # Get the data from the request:
    in_data = request.get_json()
    if not isinstance(in_data, list):
        return (
            jsonify({"error": "Data must be a list of project_id."}),
            400,
        )

    # Validate the input:
    project_ids = get_project_ids()
    for project_id in in_data:
        if not isinstance(project_id, str):
            return jsonify({"error": "Project ID must be a string."}), 400
        if project_id not in project_ids:
            return (
                jsonify({"error": f"Project ID '{project_id}' not found."}),
                400,
            )

    # Update root/starred.json:
    path = root / "starred.json"
    default_data = dict()
    data = read_optional(path=path, default=default_data)
    data["projects"] = copy.deepcopy(in_data)
    safe_dump(data, path=path, force=True)

    return jsonify({"message": "Starred projects updated successfully."}), 200


@app.route("/casm/project/<proj_id>/<obj_type>/list/")
def project_enum_list_get(proj_id, obj_type):
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

    return jsonify(data)


def main():
    """Run the CASM API server."""

    # Use argparse to get `debug` and `port` from command line arguments, if they exist:
    parser = argparse.ArgumentParser(description="Run the CASM API server.")
    parser.add_argument(
        "--debug", action="store_true", default=False, help="Enable debug mode"
    )
    args = parser.parse_args()

    import threading

    url = config["CASMVIS_API_SERVER"]
    port = int(url.split(":")[-1])

    print(f"Starting CASM API server ({url})...")

    def run_app():
        app.run(
            debug=args.debug,
            port=port,
        )

    # Start the Flask app in a separate thread
    thread = threading.Thread(target=run_app)
    thread.start()

    # time.sleep(1.0)

    # # Open the home page in the default web browser
    # webbrowser.open(f"http://localhost:{args.port}/casm")
