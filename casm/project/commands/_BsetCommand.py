from typing import Optional
from casm.project._ClexDescription import ClexDescription
from casm.project._Project import Project
from casm.project.json_io import (
    read_required,
    safe_dump,
)


class BsetCommand:
    """Methods to construct and print cluster expansion basis sets"""

    def __init__(self, proj: Project):
        self.proj = proj

    def _check_bset(
        self,
        bset: Optional[str] = None,
        clex: Optional[ClexDescription] = None,
    ):
        if bset is None and clex is None:
            if self.proj.settings.default_clex is None:
                raise Exception(
                    "No default clex found in project. One of bset, clex is required."
                )
            bset = self.proj.settings.default_clex.bset
        return bset

    def make_bspecs_template(
        self,
        name: str = None,
    ):
        """Create a bspecs.json template file"""
        return None

    def update(
        self,
        bset: Optional[str] = None,
        clex: Optional[ClexDescription] = None,
        bspecs_data: Optional[dict] = None,
        no_compile: bool = False,
        only_compile: bool = False,
    ):
        """Write and compile the Clexulator source file for a basis set

        Parameters
        ----------
        bset: Optional[str] = None
            Specify the basis set by bset name.
        clex: Optional[ClexDescription] = None
            Specify the basis set by ClexDescription.
        bspecs_data: Optional[dict] = None
            Use provided `bspecs_data` and write to `bspecs.json` instead of reading
            `bspecs.json`. Will overwrite any existing `bspecs.json` file.
        no_compile: bool = False
            If `no_compile` is True, then the Clexulator source file is written but
            not compiled. By default the Clexulator source file is immediately compiled.
        only_compile: bool = False
            If `only_compile` is True, keep the existing Clexulator source file but
            re-compile it. By default the Clexulator source file is written and then
            compiled.
        """
        print("update")
        # bset = self._check_bset(clex=clex, bset=bset)
        #
        # bspecs_path = self.proj.dir.bspecs(clex=clex, bset=bset)
        # if bspecs_data is None:
        #     bspecs_data = read_required(bspecs_path)
        # else:
        #     safe_dump(data=bspecs_data, path=bspecs_path, force=True)
        return None

    def orbit_prototypes(
        self,
        name: str = None,
    ):
        return None

    def clusters(self):
        return None

    def functions(self):
        return None
