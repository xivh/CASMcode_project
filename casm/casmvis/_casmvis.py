import argparse
import copy
import os
import pathlib
import typing
import webbrowser

from bokeh.embed import server_document
from flask import (
    Flask,
    jsonify,
    render_template,
    render_template_string,
    request,
)
from flask_cors import CORS

from casm.project.plot import ServerCache

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
    <a href="/casm"><img src="https://prisms-center.github.io/CASMcode_docs/assets/images/logo.svg" alt="CASM logo" width="200"/></a>
    <link rel="stylesheet" href="https://use.typekit.net/tlb5xuy.css"/>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
  </head>
  <body>
      <div><img src="{{ url_for('static', filename='images/logo.svg') }}" alt="My Image", width="200">
      <img src="{{ url_for('static', filename='images/logo.svg') }}" alt="My Image", width="200">
      <img src="{{ url_for('static', filename='images/logo.svg') }}" alt="My Image", width="200"></div>
      <h1><a href="/casm/project/X/enum/Y/configurations"> CASM Enum Configurations </a></h1>
  </body>
</html>
"""  # noqa: E501

enum_app_html = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>CASM Enum</title>
    <a href="/casm"><img src="https://prisms-center.github.io/CASMcode_docs/assets/images/logo.svg" alt="CASM logo" width="200"/></a>
    <link rel="stylesheet" href="https://use.typekit.net/tlb5xuy.css"/>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
  <body>
    {{ bokeh_script|safe }}
  </body>
</html>
"""  # noqa: E501

css_link_html = """
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
"""

bokeh_script_html = """
{{ bokeh_script|safe }}
"""

# --- Create a CASM project and enumerate configs ---

if False:
    import pathlib
    import shutil

    import casm.project as casmproj
    import libcasm.configuration as casmconfig
    import libcasm.xtal.prims as xtal_prims
    from casm.project.plot import (
        ConfigurationSetDashboard,
    )

    prim = casmconfig.Prim(
        xtal_prims.FCC(
            a=4.0,
            occ_dof=["Pb", "Au"],
        )
    )
    project_path = pathlib.Path("Enum_basics") / "Proj"

    if project_path.exists():
        print("Remove existing project...")
        print(project_path)
        shutil.rmtree(project_path)
        print()
    project_path.mkdir(parents=True)

    proj = casmproj.Project.init(
        path=project_path,
        prim=prim,
        name="Enum_basics",
    )

    enum = proj.enum.get("enum.1")
    enum.occ_by_supercell(max=8)

    # --- Create a Bokeh dashboard for the enumerated configurations ---
    dash = ConfigurationSetDashboard(
        configuration_set=enum.configuration_set,
    )


app = Flask(__name__)
allowed_origins = [
    "http://localhost:3000",  # casmvis client
    "http://localhost:3010",  # casmvis client - dev
]
CORS(
    app,
    resources={
        r"/casm*": {"origins": allowed_origins},
        r"/files*": {"origins": allowed_origins},
    },
)  # The * allows for /api/data and /api/data/


# @app.after_request
# def after_request(response):
#     print("after_request")
#     origin = request.headers.get("Origin")
#     print("Origin:", origin)
#     print("Allowed origins:", allowed_origins)
#     if origin in allowed_origins:
#         print("Adding headers...")
#         response.headers.add("Access-Control-Allow-Origin", origin)
#         response.headers.add(
#             "Access-Control-Allow-Headers", "Content-Type,Authorization"
#         )
#         response.headers.add(
#             "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS"
#         )
#         response.headers.add(
#             "Access-Control-Allow-Credentials", "true"
#         )  # If you need credentials.
#     else:
#         print("Origin not allowed.")
#     return response


# bokeh_process = subprocess.Popen(
#     [
#         "casmbokeh",
#     ],
#     stdout=subprocess.PIPE,
# )
#
# time.sleep(5.0)
#
#
# @atexit.register
# def kill_server():
#     bokeh_process.kill()


def make_sidebar_sections(proj_id):
    return {
        "Enum": {
            "Index": "/casm/project/{}/enum/index".format(proj_id),
            "Configurations": "/casm/project/{}/enum/configurations".format(proj_id),
        },
        "Bset": {
            "Index": "/casm/project/{}/bset/index".format(proj_id),
            "Clusters": "/casm/project/{}/bset/clusters".format(proj_id),
            "Functions": "/casm/project/{}/bset/functions".format(proj_id),
        },
        "Structure Import": {
            "Index": "/casm/project/{}/structure_import/index".format(proj_id),
            "Hull": "/casm/project/{}/structure_import/hull".format(proj_id),
        },
        "Fit": {
            "Index": "/casm/project/{}/fit/index".format(proj_id),
            "Hull": "/casm/project/{}/fit/hull".format(proj_id),
        },
    }


documentation_links = [
    {
        "name": "CASM Home",
        "url": "https://prisms-center.github.io/CASMcode_docs/",
    },
    {
        "name": "CASM Packages",
        "url": "https://prisms-center.github.io/CASMcode_pydocs/overview/latest/",
    },
]
jupyter_notebook_url = "http://localhost:8888"


def make_standard_params(proj_id):
    return dict(
        proj_id=proj_id,
        sections=make_sidebar_sections(proj_id),
        documentation_links=documentation_links,
        jupyter_notebook_url=jupyter_notebook_url,
    )


def get_project_ids():
    from casm.project.json_io import read_optional

    project_list_path = root / "project_list.json"
    default_list = list()
    data = read_optional(path=project_list_path, default=default_list)
    return [item["id"] for item in data]


def add_project(
    path: pathlib.Path,
    id: typing.Optional[str] = None,
):
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
    print("POST /files/")
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
    from casm.project.json_io import read_optional

    # read ~/.casmvis/project_list.json:

    # The project_list.json file should have the following format:
    # An array of objects, each with the following:
    #
    # generic_dof: list[string]
    #     Contains any of: "occ", "string", "disp", "magspin". These are
    #     the degrees of freedom on the prim without strain or magspin "flavor".
    # id: string
    #     An unique ID string for the project. Uses the project name by default.
    # prim_str: string
    #     The JSON string representation of the project's prim.
    # project_path: string
    #     The path to the project directory.
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
    print("Data:")
    print(data)
    starred = data.get("projects", list())
    print("Starred projects:")
    print(starred)
    return jsonify(starred)


# Put starred projects:
@app.route("/casm/project/starred/", methods=["PUT"])
def project_starred_put():
    print()
    print("PUT /casm/project/starred")

    from casm.project.json_io import read_optional, safe_dump

    # Accepts a dict with the following format:
    #
    # {
    #   <project_id>: <is_starred: boolean>
    # }

    # Get the data from the request:
    in_data = request.get_json()
    print("Input data:")
    print(in_data)
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

    print("Original data:")
    print(data)

    data["projects"] = copy.deepcopy(in_data)

    print("Updated data:")
    print(data)
    safe_dump(data, path=path, force=True)

    return jsonify({"message": "Starred projects updated successfully."}), 200


@app.route("/casm/project/<proj_id>/enum/list/")
def project_enum_list_get(proj_id):
    proj = cache.get_project(proj_id)
    data = [{"id": id} for id in proj.enum.all()]
    return jsonify(data)


@app.route("/casm/project/<proj_id>/enum/<enum_id>/configurations/")
def project_enum_configurations_get(proj_id, enum_id):
    bokeh_script = server_document(
        url="http://localhost:5006/casm/enum/configurations/",
        arguments=dict(proj_id=proj_id, enum_id=enum_id),
    )
    print("Bokeh script:")
    print(bokeh_script)
    print()

    css_link_str = render_template_string(
        css_link_html,
    )
    print("CSS link str:")
    print(css_link_str)
    print()

    bokeh_script_str = render_template_string(
        bokeh_script_html,
        bokeh_script=bokeh_script,
    )
    print("Bokeh script str:")
    print(bokeh_script_str)
    print()

    return render_template_string(
        enum_app_html,
        bokeh_script=bokeh_script,
        logo_path=logo_path,
    )
    # bset_id = "Y"
    # structure_import_id = "Y"
    # fit_id = "Y"
    #
    # return render_template(
    #     "enum_configurations.html",
    #     **make_standard_params(proj_id),
    # )


@app.route("/casm/project/<proj_id>/enum/<enum_id>/vis/configurations/")
def project_enum_vis_configurations_get(proj_id, enum_id):
    print(f"Call: /casm/project/{proj_id}/enum/{enum_id}/vis/configurations/")
    bokeh_script = server_document(
        url="http://localhost:5006/casm/enum/configurations/",
        arguments=dict(proj_id=proj_id, enum_id=enum_id),
    )
    print("Bokeh script:")
    print(bokeh_script)
    print()
    return jsonify({"bokeh_script": bokeh_script})


# config_page_1 endpoint
@app.route("/casm/project/<proj_id>/config/1/")
def config_page_1(proj_id):
    return render_template(
        "placeholder.html",
        **make_standard_params(proj_id),
    )


# config_page_2 endpoint
@app.route("/casm/project/<proj_id>/config/2/")
def config_page_2(proj_id):
    return render_template(
        "placeholder.html",
        **make_standard_params(proj_id),
    )


# config_page_3 endpoint
@app.route("/casm/project/<proj_id>/config/3/")
def config_page_3(proj_id):
    return render_template(
        "placeholder.html",
        **make_standard_params(proj_id),
    )


def main():
    # Use argparse to get `debug` and `port` from command line arguments, if they exist:
    parser = argparse.ArgumentParser(description="Run the CASM visualization server.")
    parser.add_argument(
        "--debug", action="store_true", default=False, help="Enable debug mode"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to run the server on"
    )
    args = parser.parse_args()

    import threading

    print("Starting CASM visualization server...")

    def run_app():
        app.run(
            debug=args.debug,
            port=args.port,
        )

    # Start the Flask app in a separate thread
    thread = threading.Thread(target=run_app)
    thread.start()

    # time.sleep(1.0)

    # Open the home page in the default web browser
    webbrowser.open(f"http://localhost:{args.port}/casm")
