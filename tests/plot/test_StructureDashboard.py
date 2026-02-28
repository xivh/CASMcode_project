import pathlib

import darkdetect

import libcasm.xtal.structures as xtal_structures
from casm.project.plot import (
    StructureDashboard,
)
from casm.vis import (
    add_application,
)


def test_StructureDashboard_1():
    structure = xtal_structures.FCC(
        a=4.0,
        atom_type="A",
    )
    dash = StructureDashboard(
        structure=structure,
        structure_name="FCC",
    )

    def modify_doc(doc):
        print("modify_doc")
        layout = dash.make_layout()
        doc.add_root(layout)

        if darkdetect.isDark():
            doc.theme = "carbon"

    add_application(
        url=pathlib.Path("/casm/dash/structure/"),
        app=modify_doc,
    )

    assert True

    # try:
    #     start_applications()
    # except KeyboardInterrupt:
    #     print()
    #     print("Shutting down CASM Bokeh server...")
    #     print()
