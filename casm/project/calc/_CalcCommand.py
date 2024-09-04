from typing import Iterable, Optional, Union

import libcasm.configuration as casmconfig
from casm.project._Project import Project


class CalcCommand:
    """Methods to interact with DFT or atomistic calculators"""

    def __init__(self, proj: Project):
        self.proj = proj

    def setup_vasp(
        self,
        configurations: Union[
            Iterable[casmconfig.Configuration], casmconfig.ConfigurationSet
        ],
        calctype: str,
    ):
        """Setup VASP calculations

        Parameters
        ----------
        configurations: Union[Iterable[libcasm.configuration.Configuration], \
        libcasm.configuration.ConfigurationSet]
            The candidate configurations. Must be a
            :class:`~libcasm.configuration.ConfigurationSet` or an iterable of
            :class:`~libcasm.configuration.Configuration`.

        calctype: str
            The calctype is used by CASM to find a calc.json file with VASP settings.

        id: Optional[str] = None
            An optional calculation identifier string specifying where a record
            of this set of calculations is stored. Calculation data is stored in a
            CASM project at
            `<project>/calculations/calc.<id>/`. If None, a sequential id is
            generated automatically.


        Returns
        -------
        id: str
            Calculation ID allows for finding information about the calculation that
            were setup. This can be used later with `calc_vasp` or `report_vasp` or
            with imports.
        """
        print("setup_vasp: Create VASP calculation input files")
        return None

    def calc_vasp(
        self,
        id: Optional[str] = None,
    ):
        print("calc_vasp: Run VASP calculations")
        return None

    def report_vasp(
        self,
        batchfile: Optional[str] = None,
        id: Optional[str] = None,
    ):
        """Report VASP calculations, converting to libcasm.xtal.Structure

        Parameters
        ----------
        batchile: Optional[str] = None
            TODO: This needs some work... Something to indicate VASP calculations
            performed outside that should be read and converted to
            libcasm.xtal.Structure

        id: Optional[str] = None
            An optional calculation identifier string specifying where a record
            of this set of calculations is stored. Calculation data is stored in a
            CASM project at
            `<project>/calculations/calc.<id>/`. If None, a sequential id is
            generated automatically.


        Returns
        -------
        id: str
            Calculation ID allows for finding information about the calculation that
            were setup. This can be used later with `calc_vasp` or `report_vasp` or
            with imports.
        """
        print(
            "report_vasp: "
            "Parse VASP calculation output files and convert to libcasm.xtal.Structure"
        )
        return None
