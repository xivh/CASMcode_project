import os
import subprocess
import sys
import tempfile
import typing

import bokeh.models
from bokeh.layouts import column

import libcasm.xtal as xtal

from ._DashboardStyles import DashboardStyles


def vesta_installed() -> bool:
    """Check if VESTA is installed on the system.

    For MacOS, it checks if VESTA is installed in the /Applications/VESTA directory.
    For Linux, it checks if VESTA is accessible via the command line as `vesta`.

    Returns
    -------
    bool
        True if VESTA is installed, False otherwise.
    """
    if sys.platform == "darwin":
        return os.path.exists("/Applications/VESTA/VESTA.app")
    elif sys.platform.startswith("linux"):
        from shutil import which

        return which("vesta") is not None
    else:
        return False


def open_structure_with_vesta(
    structure: xtal.Structure,
    structure_name: str,
):
    """Open a structure in VESTA using a subprocess call.

    This function creates a temporary POSCAR file and opens it in VESTA.

    For MacOS:
    - ensure that VESTA is installed in the /Applications/VESTA directory.
    - The `open` command is used to launch VESTA with the specified file, as with
      ``open -a /Applications/VESTA/VESTA.app filename.vasp``, where `filename.vasp`
      is the name of the temporary POSCAR file.

    For Linux:
    - ensure that VESTA is installed and accessible via the command line as `vesta`.
    - The command `vesta filename.vasp` is used to launch VESTA, where `filename.vasp`
      is the name of the temporary POSCAR file.

    Parameters
    ----------
    structure: libcasm.xtal.Structure
        The structure to open in VESTA.
    structure_name: str
        The name of the structure, used to name the temporary file.

    """
    if structure is None:
        return

    name = structure_name.replace("/", ".") + ".vasp"
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, name)
    with open(file_path, "w") as f:
        print(structure.to_poscar_str())
        f.write(structure.to_poscar_str())
        f.flush()
        os.fsync(f.fileno())

    if sys.platform == "darwin":
        cmd = ["open", "-a", "/Applications/VESTA/VESTA.app", file_path]
    elif sys.platform.startswith("linux"):
        # Try to use VESTA if installed, otherwise fallback to xdg-open
        cmd = ["vesta", file_path]
    else:
        raise RuntimeError("Unsupported OS for opening VESTA")

    subprocess.run(cmd)


class OpenWithButton:
    """A button that opens the selected structure in an external program."""

    def __init__(
        self,
        program_name: str = "VESTA",
        callback: typing.Callable[
            [xtal.Structure, str], None
        ] = open_structure_with_vesta,
        parent: typing.Any = None,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        program_name: str = "VESTA"
            The name of the program to open the structure with, used to label the
            button.

        callback: Callable[[xtal.Structure, str], None] = open_structure_with_vesta
            A function that takes a :class:`~libcasm.xtal.Structure` and its name as
            input, and opens it in an external program using a subprocess call.

        parent: Any = None
            The parent dashboard or component that contains this button. This is used
            to access the selected structure and its name.
        """
        self.program_name = program_name
        self.callback = callback
        self.parent = parent

    def make_layout(
        self,
        styles: DashboardStyles = None,
    ):
        """Return the layout containing the button."""

        open_with_button = bokeh.models.Button(
            label=f"Open with {self.program_name}",
            button_type="success",
        )

        def _on_click(attr):

            structure = self.parent.selected_structure
            structure_name = self.parent.selected_structure_name

            self.callback(structure=structure, structure_name=structure_name)

        open_with_button.on_click(_on_click)

        return column(
            open_with_button,
            margin=(10, 20),
        )
