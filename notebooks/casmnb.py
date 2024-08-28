import glob
import os
import pathlib

_tmp_dir = None


def tmp_dir():
    global _tmp_dir
    if _tmp_dir is None:
        import tempfile

        _tmp_dir = tempfile.TemporaryDirectory()
    return pathlib.Path(_tmp_dir.name)


def notebook_dir():
    return pathlib.Path(os.path.dirname(os.path.realpath(__file__))).resolve()


def input_dir():
    return notebook_dir() / "input"


def prim_dir():
    return input_dir() / "prim"


def list_example_prim():
    prim_files = glob.glob(str(prim_dir() / "*_prim.json"))
    print("Example prims:")
    for file in prim_files:
        print(f"- {pathlib.Path(file).name}")


def autoconfigure():
    # Configure environment variables:
    if "CASM_PREFIX" not in os.environ:
        import casm.bset

        print("Autoconfigure...")
        casm.bset.autoconfigure()
        print("Autoconfigure DONE")
