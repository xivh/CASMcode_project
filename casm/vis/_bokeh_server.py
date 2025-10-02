import pathlib
import shutil
import sys

import darkdetect

import casm.project as casmproj
import libcasm.configuration as casmconfig
import libcasm.xtal.prims as xtal_prims
from casm.project.plot import (
    ConfigurationListDashboardv2,
    ConfigurationSetDashboardv2,
    PrimDashboard,
)

from ._BokehServerManager import (
    add_application,
    start_applications,
)
from ._functions import (
    get_required_argument,
)
from ._ServerCache import (
    ServerCache,
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


def add_casm_prim_vis(cache: ServerCache):
    bokeh_app_path = "/casm/prim/vis/"

    def modify_doc(doc):
        # print("Begin /casm/prim/vis/")

        try:

            proj_id = get_required_argument(doc, "proj_id")

            session_id = doc.session_context.id if doc.session_context else id(doc)
            app_key = (bokeh_app_path, proj_id, session_id)

            app = cache.app.get(app_key)
            if app is None:
                # If not already existing, create a new obj
                proj = cache.get_project(proj_id)

                app = PrimDashboard(
                    prim=proj.prim,
                    views_dir=proj.dir.views_dir(),
                )
                cache.app[app_key] = app

            # Overall layout
            layout = app.make_layout()

        except Exception as e:
            from bokeh.layouts import column
            from bokeh.models import Div

            error_div = Div(
                text=f"<h3>Error:</h3><p style='color: red;'>{str(e)}</p>",
                width=800,
                height=200,
            )
            layout = column(error_div)

        doc.add_root(layout)

        if darkdetect.isDark():
            doc.theme = "carbon"

    add_application(
        url=pathlib.Path(bokeh_app_path),
        app=modify_doc,
    )


def add_casm_enum_vis(cache: ServerCache):
    bokeh_app_path = "/casm/enum/vis/"

    def modify_doc(doc):
        # print("Begin /casm/enum/vis/")

        try:
            proj_id = get_required_argument(doc, "proj_id")
            enum_id = get_required_argument(doc, "obj_id")
            view_id = get_required_argument(doc, "view_id")

            session_id = doc.session_context.id if doc.session_context else id(doc)
            app_key = (bokeh_app_path, proj_id, enum_id, view_id, session_id)

            app = cache.app.get(app_key)
            if app is None:
                # If not already existing, create a new obj
                proj = cache.get_project(proj_id)
                enum = proj.enum.get(id=enum_id)

                if view_id == "configuration_set":
                    app = ConfigurationSetDashboardv2(
                        prim=proj.prim,
                        configuration_set=enum.configuration_set,
                        views_dir=proj.dir.views_dir(),
                    )
                elif view_id == "configuration_list":
                    app = ConfigurationListDashboardv2(
                        prim=proj.prim,
                        configuration_list=enum.configuration_list,
                        views_dir=proj.dir.views_dir(),
                    )
                else:
                    raise ValueError(f"Unknown view_id: {view_id}")
                cache.app[app_key] = app

            # Overall layout
            layout = app.make_layout()

        except Exception as e:
            from bokeh.layouts import column
            from bokeh.models import Div

            error_div = Div(
                text=f"<h3>Error:</h3><p style='color: red;'>{str(e)}</p>",
                width=800,
                height=200,
            )
            layout = column(error_div)

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
    add_casm_prim_vis(cache=cache)
    add_casm_enum_vis(cache=cache)

    try:
        start_applications()
    except KeyboardInterrupt:
        print()
        print("Shutting down CASM Bokeh server...")
        print()
