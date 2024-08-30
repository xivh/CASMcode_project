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


def notebooks_dir():
    return pathlib.Path(os.path.dirname(os.path.realpath(__file__))).resolve()


def input_dir():
    return notebooks_dir() / "input"


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


def simple_style():
    """Reduce header sizes for a simple style."""
    from IPython.core.display import HTML, display

    # /*
    # :root {
    #   --jp-content-line-height: 1.6;
    #   --jp-content-font-scale-factor: 1.2;
    #   --jp-content-font-size0: 0.83333em;
    #   --jp-content-font-size1: 14px; /* Base font size */
    #   --jp-content-font-size2: 1.2em;
    #   --jp-content-font-size3: 1.44em;
    #   --jp-content-font-size4: 1.728em;
    #   --jp-content-font-size5: 2.0736em;
    # }
    # */

    display(
        HTML(
            """
<style>
/* Styling Markdown */
/* Headings */


.jp-RenderedHTMLCommon h1 {
  font-weight: bold;
  font-size: var(--jp-content-font-size3);
}

.jp-RenderedHTMLCommon h2 {
  font-weight: bold;
  font-size: var(--jp-content-font-size2);
}

.jp-RenderedHTMLCommon h3 {
  font-weight: bold;
  font-size: var(--jp-content-font-size1);
}

.jp-RenderedHTMLCommon h4 {
  font-weight: bold;
  font-size: 1.1em;
}

</style>
"""
        )
    )
