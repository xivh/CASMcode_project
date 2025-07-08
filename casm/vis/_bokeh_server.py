import pathlib
import shutil
import sys

import darkdetect

import casm.project as casmproj
import libcasm.configuration as casmconfig
import libcasm.xtal.prims as xtal_prims
from casm.project.plot import (
    ConfigurationListDashboard,
    ConfigurationSetDashboard,
    ServerCache,
    add_application,
    start_applications,
)

from ._functions import (
    get_required_argument,
)


def test_project():
    print("~~~ CASM visualizations ~~~")
    print("args: ", sys.argv)
    print()

    # --- Create a CASM project and enumerate configs ---
    prim = casmconfig.Prim(
        xtal_prims.FCC(
            a=4.0,
            occ_dof=["A", "B"],
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

    # dash = ConfigurationSetDashboard(
    #     configuration_set=enum.configuration_set,
    # )
    # dash.add()


def add_casm_enum_vis(cache: ServerCache):
    bokeh_app_path = "/casm/enum/vis/"

    def modify_doc(doc):
        print("Begin /casm/enum/vis/")

        proj_id = get_required_argument(doc, "proj_id")
        enum_id = get_required_argument(doc, "obj_id")
        view_id = get_required_argument(doc, "view_id")
        print("proj_id:", proj_id)
        print("enum_id:", enum_id)
        print("view_id:", view_id)

        app_key = (bokeh_app_path, proj_id, enum_id, view_id)

        app = cache.app.get(app_key)
        if app is None:
            # If not already existing, create a new obj
            proj = cache.get_project(proj_id)
            enum = proj.enum.get(id=enum_id)

            if view_id == "configuration_set":
                app = ConfigurationSetDashboard(
                    configuration_set=enum.configuration_set,
                )
            elif view_id == "configuration_list":
                app = ConfigurationListDashboard(
                    configuration_list=enum.configuration_list,
                    page_size=100,
                )
            else:
                raise ValueError(f"Unknown view_id: {view_id}")
            cache.app[app_key] = app

        # Overall layout
        layout = app.make_layout()

        doc.add_root(layout)

        if darkdetect.isDark():
            doc.theme = "carbon"

    add_application(
        url=pathlib.Path(bokeh_app_path),
        app=modify_doc,
    )


def main():
    cache = ServerCache()

    # casm project visualizations
    add_casm_enum_vis(cache=cache)

    try:
        start_applications()
    except KeyboardInterrupt:
        print()
        print("Shutting down CASM Bokeh server...")
        print()
