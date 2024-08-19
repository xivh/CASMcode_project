import os
import pathlib
import shutil
import sys

import pytest

import libcasm.xtal as xtal
from casm.project import Project


def _win32_longpath(path):
    """
    Helper function to add the long path prefix for Windows, so that shutil.copytree
     won't fail while working with paths with 255+ chars.
    """
    if sys.platform == "win32":
        # The use of os.path.normpath here is necessary since "the "\\?\" prefix
        # to a path string tells the Windows APIs to disable all string parsing
        # and to send the string that follows it straight to the file system".
        # (See https://docs.microsoft.com/pt-br/windows/desktop/FileIO/naming-a-file)
        return "\\\\?\\" + os.path.normpath(path)
    else:
        return path


@pytest.fixture(scope="session")
def session_shared_datadir(tmpdir_factory):
    original_shared_path = pathlib.Path(os.path.realpath(__file__)).parent / "data"
    session_temp_path = tmpdir_factory.mktemp("session_data")
    shutil.copytree(
        _win32_longpath(original_shared_path),
        _win32_longpath(str(session_temp_path)),
        dirs_exist_ok=True,
    )
    return session_temp_path


@pytest.fixture
def ZrO_tmp_project(tmp_path):
    os.chdir(tmp_path)
    project_path = tmp_path / "ZrO"
    project_path.mkdir(parents=True, exist_ok=True)

    basis = [
        {
            "coordinate": [0.0, 0.0, 0.0],
            "occupants": ["Zr"],
        },
        {"coordinate": [2.0 / 3.0, 1.0 / 3.0, 1.0 / 2.0], "occupants": ["Zr"]},
        {"coordinate": [1.0 / 3.0, 2.0 / 3.0, 1.0 / 4.0], "occupants": ["Va", "O"]},
        {"coordinate": [1.0 / 3.0, 2.0 / 3.0, 3.0 / 4.0], "occupants": ["Va", "O"]},
    ]

    prim_data = {
        "basis": basis,
        "coordinate_mode": "Fractional",
        "lattice_vectors": [
            [3.233986856383, 0.000000000000, 0.000000000000],
            [-1.616993428191, 2.800714773133, 0.000000000000],
            [0.000000000000, 0.000000000000, 5.168678340000],
        ],
        "title": "ZrO",
    }

    with open(project_path / "prim.json", "w") as f:
        f.write(xtal.pretty_json(prim_data))

    project = Project.init(path=project_path)

    ## calculation settings ##
    calctype_settings_dir = project.dir.calctype_settings_dir_v2(
        calctype="vasp.default",
    )
    calctype_settings_dir.mkdir(parents=True, exist_ok=True)
    with open(calctype_settings_dir / "INCAR", "w") as f:
        f.write(
            """ISPIN = 1 #does non spin-polarized calc.
PREC = Accurate #cutoff + wrap around errors.
IBRION= 2 #conj. grad. relaxation.
NSW=61 #numberof ionic steps taken in minimization. Make it odd.
ISIF= 3 #whether stress tensor is calculated, what is allowed to relax.
ENMAX=600 #cutoff
ISMEAR = 1 #BZ integration method (for relaxation runs).
SIGMA = 0.2 #smearing width (keep T*S < 1meV/atom). 
LWAVE = .FALSE.
LCHARG = .FALSE.
"""
        )
    with open(calctype_settings_dir / "KPOINTS", "w") as f:
        f.write(
            """Fully automatic mesh
0              ! 0 -> automatic generation scheme 
Auto           ! fully automatic
  10           ! length (R_k)
"""
        )

    return project
