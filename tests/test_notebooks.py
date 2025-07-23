import os
import pathlib
import shutil

import nbformat
import pytest
from nbconvert.preprocessors import ExecutePreprocessor

repo_dir = pathlib.Path(os.path.abspath(__file__)).parent.parent


def execute_notebook(exec_dir: pathlib.Path, notebook_path: pathlib.Path):
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
        try:
            ep.preprocess(nb, {"metadata": {"path": str(exec_dir)}})
        except Exception:
            assert False, f"Failed executing {notebook_path}"


@pytest.mark.requires_ase
def test_SiGe_occ_part1():
    exec_dir = repo_dir / "notebooks"
    notebook_path = exec_dir / "SiGe_occ_part1.ipynb"
    print(notebook_path)
    execute_notebook(
        exec_dir=notebook_path.parent,
        notebook_path=notebook_path,
    )

    # cleanup
    shutil.rmtree(exec_dir / "SiGe_occ")


def test_Bset_basics():
    exec_dir = repo_dir / "notebooks"
    notebook_path = exec_dir / "Bset_basics.ipynb"
    print(notebook_path)
    execute_notebook(
        exec_dir=notebook_path.parent,
        notebook_path=notebook_path,
    )

    # cleanup
    shutil.rmtree(exec_dir / "Proj")
