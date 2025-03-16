import pathlib
import shutil
import sys

import casm.project as casmproj
import libcasm.configuration as casmconfig
import libcasm.xtal.prims as xtal_prims
from casm.project.plot import (
    ConfigurationSetDashboard,
    ServerCache,
    start_applications,
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


def main():
    cache = ServerCache()

    ConfigurationSetDashboard.add(cache=cache)

    start_applications()
