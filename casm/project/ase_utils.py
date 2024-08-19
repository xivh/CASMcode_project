import os
import pathlib
from typing import Callable

import ase
import ase.calculators.vasp

import libcasm.xtal as xtal


def make_ase_atoms(casm_structure: xtal.Structure) -> ase.Atoms:
    """Given a CASM Structure , convert it to an ASE Atoms

    .. attention::

        This method only works for non-magnetic atomic structures. If the structure
        contains molecular information, an error will be raised.

    Parameters
    ----------
    casm_structure : xtal.Structure

    Returns
    -------
    ase.Atoms

    """
    if len(casm_structure.mol_type()):
        raise ValueError(
            "Error: only non-magnetic atomic structures may be converted using "
            "to_ase_atoms"
        )

    symbols = casm_structure.atom_type()
    positions = casm_structure.atom_coordinate_cart().transpose()
    cell = casm_structure.lattice().column_vector_matrix().transpose()

    return ase.Atoms(
        symbols=symbols,
        positions=positions,
        cell=cell,
        pbc=True,
    )


def make_casm_structure(ase_atoms: ase.Atoms) -> xtal.Structure:
    """Given an ASE Atoms, convert it to a CASM Structure

    .. attention::

        This method only works for non-magnetic atomic structures.

    Parameters
    ----------
    ase_atoms : ase.Atoms
        A :class:`ase.Atoms` object

    Returns
    -------
    casm_structure: libcasm.xtal.Structure
        A :class:`~libcasm.xtal.Structure` object

    """

    lattice = xtal.Lattice(
        column_vector_matrix=ase_atoms.get_cell().transpose(),
    )
    atom_coordinate_frac = ase_atoms.get_scaled_positions().transpose()
    atom_type = ase_atoms.get_chemical_symbols()

    return xtal.Structure(
        lattice=lattice,
        atom_coordinate_frac=atom_coordinate_frac,
        atom_type=atom_type,
    )


class AseVaspTool:
    def __init__(
        self,
        calctype_settings_dir: pathlib.Path,
        setups: dict,
        xc: str,
    ):
        """Setup, run, and collect VASP calculations using ASE.

        For details on the parameters, see the `ase documentation for the vasp
        calculator <https://wiki.fysik.dtu.dk/ase/ase/calculators/vasp.html>`.

        .. attention::

            ase assumes that POTCAR files exist in one of `potpaw_PBE`, `potpaw`, or
            `potpaw_GGA`, located at the path specified by the environment
            variable VASP_PP_PATH.

        Parameters
        ----------
        calctype_settings_dir: pathlib.Path
            Path to the directory containing INCAR and KPOINTS files.
        setups: dict
            Dictionary of pseudopotential setups for each element.
        xc: str
            Exchange-correlation type, one of: "pbe", "lda", or "pw91"
        """
        if "VASP_PP_PATH" not in os.environ:
            raise ValueError(
                "Please set the environment variable VASP_PP_PATH to the directory "
                "containing the VASP POTCAR files. It should contain the directories "
                "potpaw_PBE, potpaw, and potpaw_GGA."
            )

        self.incar_path = calctype_settings_dir / "INCAR"
        """pathlib.Path: Path to the INCAR file."""

        self.kpoints_path = calctype_settings_dir / "KPOINTS"
        """pathlib.Path: Path to the KPOINTS file."""

        self.setups = setups
        """dict: Dictionary of pseudopotential setups for each element."""

        self.xc = xc
        """str: Exchange-correlation type, one of: "pbe", "lda", or "pw91" """

    def make_calculator(
        self,
        ase_atoms: ase.Atoms,
        calc_dir: pathlib.Path,
    ) -> ase.calculators.vasp.Vasp:
        calc_dir.mkdir(parents=True, exist_ok=True)

        vasp_calculator = ase.calculators.vasp.Vasp(
            atoms=ase_atoms,
            directory=calc_dir,
            setups=self.setups,
            xc=self.xc,
        )
        vasp_calculator.read_incar(self.incar_path)
        vasp_calculator.read_kpoints(self.kpoints_path)
        return vasp_calculator

    def setup(
        self,
        casm_structure: xtal.Structure,
        calc_dir: pathlib.Path,
        make_ase_atoms_f: Callable[[xtal.Structure], ase.Atoms] = make_ase_atoms,
    ) -> ase.calculators.vasp.Vasp:
        """Setup a VASP calculation for a given structure.

        Parameters
        ----------
        casm_structure: libcasm.xtal.Structure
            The structure to calculate.
        calc_dir: pathlib.Path
            The directory in which to store the calculation files.
        make_ase_atoms_f: Callable[[xtal.Structure], ase.Atoms] = make_ase_atoms
            A function to convert the CASM structure to an ASE Atoms object. The
            default function, :func:`make_ase_atoms` works for non-magnetic atomic
            structures.

        Returns
        -------
        vasp_calculator: ase.calculators.vasp.Vasp
            The ASE VASP calculator object.
        """
        ase_atoms = make_ase_atoms_f(casm_structure)
        vasp_calculator = self.make_calculator(ase_atoms=ase_atoms, calc_dir=calc_dir)

        # Write INCAR, KPOINTS, POTCAR, POSCAR
        vasp_calculator.write_input(atoms=ase_atoms)
        return vasp_calculator
