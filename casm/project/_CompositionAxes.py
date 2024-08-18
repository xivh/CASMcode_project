import pathlib
import sys
from typing import Optional, TextIO, TypeVar

import libcasm.casmglobal as casmglobal
import libcasm.xtal as xtal
from libcasm.composition import (
    CompositionCalculator,
    CompositionConverter,
    make_standard_origin_and_end_members,
)

from ._ConfigCompositionCalculator import ConfigCompositionCalculator
from .json_io import (
    read_required,
    safe_dump,
)


def make_chemical_components(
    xtal_prim: xtal.Prim,
    sort: bool = True,
):
    """Make components and allowed_occs for a chemical composition calculator

    Notes
    -----

    - This function is used to make a
      :class:`~libcasm.composition.CompositionCalculator` in which occupants which
      are the same chemistry but different magnetic spin, or molecular orientation, etc.
      are treated as a single component.

    Parameters
    ----------
    xtal_prim: libcasm.xtal.Prim
        The prim.

    sort: bool = True
        By default, components are sorted. If `sort` is False, then the components
        are ordered as found iterating over `Prim.occ_dof`.

    Returns
    -------
    components: list[str],
        The requested component order in the composition vectors. Occupants
        are distinguished by `Occupant.name` (the chemical name).

    allowed_occs: list[list[str]],
        For each sublattice, a vector of components allowed to occupy
        the sublattice.
    """
    components = []
    allowed_occs = []

    occupants = xtal_prim.occupants()
    occ_dof = xtal_prim.occ_dof()
    for site_occ_dof in occ_dof:
        site_allowed_occs = []
        for occ_id in site_occ_dof:
            occupant = occupants[occ_id]
            if occupant.name() not in components:
                components.append(occupant.name())
            site_allowed_occs.append(occupant.name())
        allowed_occs.append(site_allowed_occs)

    if sort:
        components.sort()
    return (components, allowed_occs)


def make_occupant_components(
    xtal_prim: xtal.Prim,
    sort: bool = True,
):
    """Make components and allowed_occs for a unique occupant composition calculator

    Notes
    -----

    - This function is used to make a
      :class:`~libcasm.composition.CompositionCalculator` in which occupants which
      are the same chemistry but different magnetic spin, or molecular orientation, etc.
      are treated as different components.

    Parameters
    ----------
    xtal_prim: libcasm.xtal.Prim
        The prim.

    sort: bool = True
        By default, components are sorted. If `sort` is False, then the components
        are ordered as found iterating over `Prim.occ_dof`.

    Returns
    -------
    components: list[str],
        The requested component order in the composition vectors. Occupants
        are distinguished by label in the `Prim.occ_dof` lists
        (the unique name / orientation name).

    allowed_occs: list[list[str]],
        For each sublattice, a vector of components allowed to occupy
        the sublattice.
    """
    components = []
    allowed_occs = []

    occ_dof = xtal_prim.occ_dof()
    for site_occ_dof in occ_dof:
        site_allowed_occs = []
        for occ_id in site_occ_dof:
            if occ_id not in components:
                components.append(occ_id)
            site_allowed_occs.append(occ_id)
        allowed_occs.append(site_allowed_occs)

    if sort:
        components.sort()
    return (components, allowed_occs)


def make_standard_axes(
    components: list[str],
    allowed_occs: list[list[str]],
    tol: float = casmglobal.TOL,
) -> tuple[CompositionCalculator, list[CompositionConverter]]:
    """Make composition calculator and standard axes

    Parameters
    ----------
    components: list[str],
        The requested component order in the composition vectors.

    allowed_occs: list[list[str]]
        For each sublattice, a vector of components allowed to occupy the sublattice.

    tol: float = libcasm.casmglobal.TOL
        Tolerance for comparison. Used to find composition axes such that the
        parametric composition parameters are non-negative.

    Returns
    -------
    calculator: libcasm.composition.CompositionCalculator
        The composition calculator.

    standard_axes: list[libcasm.composition.CompositionConverter]
        A list of :class:`~libcasm.composition.CompositionConverter` for
        standard composition axes.
    """
    calculator = CompositionCalculator(
        components=components,
        allowed_occs=allowed_occs,
    )
    standard_origin_and_end_members = make_standard_origin_and_end_members(
        components=components,
        allowed_occs=allowed_occs,
        tol=tol,
    )

    axes = []
    for choice in standard_origin_and_end_members:
        axes.append(
            CompositionConverter(
                components=components,
                origin_and_end_members=choice,
            )
        )
    return (calculator, axes)


CompositionAxesType = TypeVar("CompositionAxesType")


class CompositionAxes:
    """Store, access, and use composition axes

    This class is used to:

    - make a :class:`~libcasm.composition.CompositionCalculator`
    - make and store a list of :class:`~libcasm.composition.CompositionConverter`, the
      possible parametric composition axes
    - store which :class:`~libcasm.composition.CompositionConverter` is the default
      axes choice.

    """

    def __init__(self, path: Optional[pathlib.Path] = None):
        """
        .. rubric:: Constructor

        Notes
        -----

        It is expected that OccupantCompositionAxes is constructed using one of:

        - :func:`~casm.project.OccupantCompositionAxes.init`
        - :func:`~casm.project.OccupantCompositionAxes.from_dict`

        Parameters
        ----------
        path: Optional[pathlib.Path] = None
            Path to the axes file, for `load` and `commit`.

        """

        self.path = path
        """Optional[pathlib.Path]: Path to the axes file, for `load` and `commit`."""

        self.components = None
        """Optional[list[str]]: The component order in the composition vectors.

        A user may customize the order of components in this list to adjust the order
        of components in the calculated composition vectors.
        """

        self.allowed_occs = None
        """Optional[list[list[str]]]: For each sublattice, a vector of components \
        allowed to occupy the sublattice.

        The values must be elements in `components`. The order must be consistent 
        with the order of occupants listed in `xtal.Prim.occ_dof`. This should be 
        used as calculated.
        """

        self.calculator = None
        """Optional[CompositionCalculator]: Composition calculator"""

        self.enumerated = []
        """list[str]: Keys of enumerated standard axes

        This is populated by the `calculate` method.
        """

        self.possible_axes = {}
        """dict[str, CompositionConverter]: All possible axes, enumerated and custom, \
        by id string.

        The enumerated axes are constructed by the `calculate` method. The custom
        axes are user provided.
        """

        self.current_axes = None
        """Optional[str]: Key of current axes in `self.possible_axes`"""

    def set_current_axes(self, key: Optional[str]):
        """Select the current composition axes

        Parameters
        ----------
        key: Optional[str]
            The key of one of the `possible_axes` to set as the current axes. If None,
            then the current axes are cleared. If `key` is not found, then a ValueError
            is raised.
        """
        if key is None:
            self.current_axes = None
            return
        key = str(key)
        if key not in self.possible_axes:
            raise ValueError(
                f"Error in CompositionAxes.select: '{key}' not found in possible_axes"
            )
        self.current_axes = key

    def _assign_from_dict(self, data: dict):
        self.allowed_occs = data["allowed_occs"]
        self.components = data["components"]
        self.enumerated = data["enumerated"]
        self.possible_axes = {
            key: CompositionConverter.from_dict(x)
            for key, x in data["possible_axes"].items()
        }
        self.current_axes = data["current_axes"]
        self.calculator = CompositionCalculator(
            components=self.components,
            allowed_occs=self.allowed_occs,
        )

    def load(self):
        if self.path is None:
            raise ValueError("Error in CompositionAxes.load: path is None")
        data = read_required(self.path)
        self._assign_from_dict(data)

    def commit(self):
        if self.path is None:
            raise ValueError("Error in CompositionAxes.commit: path is None")
        safe_dump(self.to_dict(), self.path, force=True, quiet=True)

    def print_table(
        self,
        out: Optional[TextIO] = None,
    ):
        """List the possible composition axes

        Parameters
        ----------
        out: Optional[TextIO] = None
            Output stream. Defaults to `sys.stdout
        """

        # Possible composition axes:
        #
        #        KEY     ORIGIN          a     GENERAL FORMULA
        #        ---        ---        ---     ---
        #          0          B          A     A(a)B(1-a)
        #          1          A          B     A(1-a)B(a)

        from ._misc import print_table

        columns = ["KEY", "ORIGIN"]
        for key, value in self.possible_axes.items():
            for i, label in enumerate(value.axes()):
                if i == 0:
                    columns.append(label)
            break
        columns.append("GENERAL FORMULA")

        data = []
        for key, value in self.possible_axes.items():
            _data = {
                "KEY": key,
                "ORIGIN": value.origin_formula(),
                "GENERAL FORMULA": value.mol_formula(),
            }
            for i, label in enumerate(value.axes()):
                _data[label] = value.end_member_formula(i)
            data.append(_data)

        print_table(data=data, columns=columns, headers=columns, out=out)

    def print_current_axes(
        self,
        out: Optional[TextIO] = None,
    ):
        # Currently selected composition axes: 0
        #
        # Parametric composition:
        #   comp(a) = 0.5*comp_n(A)  - 0.5*(comp_n(B) - 1)
        #
        # Composition:
        #   comp_n(A) = 1*comp(a)
        #   comp_n(B) = 1 - 1*comp(a)
        #
        # Parametric chemical potentials:
        #   param_chem_pot(a) = chem_pot(A) - chem_pot(B)

        if out is None:
            out = sys.stdout

        if self.current_axes is None:
            out.write("No composition axes selected\n")
            return
        if self.current_axes not in self.possible_axes:
            raise ValueError(
                "Error in CompositionAxes.print_current_axes: "
                f"current_axes ('{self.current_axes}') not found in possible_axes\n"
            )

        axes = self.possible_axes.get(self.current_axes)

        out.write(f"Currently selected composition axes: {self.current_axes}\n")
        out.write("\n")
        out.write("Parametric composition:\n")
        for i in range(axes.independent_compositions()):
            out.write(f"  {axes.param_component_formula(i)}\n")
        out.write("\n")
        out.write("Composition:\n")
        for i in range(len(axes.components())):
            out.write(f"  {axes.mol_component_formula(i)}\n")
        out.write("\n")
        out.write("Parametric chemical potentials:\n")
        for i in range(axes.independent_compositions()):
            out.write(f"  {axes.param_chem_pot_formula(i)}\n")

    def __repr__(self):
        from io import StringIO

        out = StringIO()
        self.print_table(out)
        out.write("\n")
        self.print_current_axes(out)
        return out.getvalue().strip()

    @property
    def config_composition(self) -> ConfigCompositionCalculator:
        return ConfigCompositionCalculator(
            calculator=self.calculator,
            converter=self.possible_axes.get(self.current_axes),
        )

    @staticmethod
    def init(
        components: list[str],
        allowed_occs: list[list[str]],
        path: Optional[pathlib.Path] = None,
        tol: float = casmglobal.TOL,
    ):
        """Initialize with standard axes

        Parameters
        ----------
        components: list[str]
            The requested component order in the composition vectors.
        allowed_occs: list[list[str]]
            For each sublattice, a vector of components allowed to occupy the
            sublattice. This must be consistent with the prim.
        path: Optional[pathlib.Path] = None,
            Path to the axes file, for `load` and `commit`.
        tol: float = libcasm.casmglobal.TOL
            Tolerance for comparison. Used to find composition axes such that the
            parametric composition parameters are non-negative

        Returns
        -------
        value: CompositionAxes
            CompositionAxes with standard axes and calculator. The current axes are
            set to `"0"` by default.
        """
        value = CompositionAxes(path=path)
        value.components = components
        value.allowed_occs = allowed_occs
        value.calculator, enumerated_axes = make_standard_axes(
            components=components,
            allowed_occs=allowed_occs,
            tol=tol,
        )
        for i, axes in enumerate(enumerated_axes):
            key = f"{i}"
            value.possible_axes[key] = axes
            value.enumerated.append(key)
        return value

    @staticmethod
    def init_chemical_axes(
        xtal_prim: xtal.Prim,
        sort: bool = True,
        path: Optional[pathlib.Path] = None,
        tol: float = casmglobal.TOL,
    ) -> CompositionAxesType:
        """Initialize with the standard chemical composition axes

        Notes
        -----

        - Occupants which are the same chemistry but different magnetic spin, or
          molecular orientation, etc. are treated as the same component.

        Parameters
        ----------
        xtal_prim: libcasm.xtal.Prim
            The prim.
        sort: bool = True
            If `self.components` is None, then `self.calculator` is re-generated.
            By default, components are sorted. If `sort` is False, then the components
            are ordered as found iterating over `Prim.occ_dof`.
        tol: float = libcasm.casmglobal.TOL
            Tolerance for comparison. Used to find composition axes such that the
            parametric composition parameters are non-negative

        """

        components, allowed_occs = make_chemical_components(
            xtal_prim=xtal_prim,
            sort=sort,
        )
        return CompositionAxes.init(
            components=components,
            allowed_occs=allowed_occs,
            path=path,
            tol=tol,
        )

    @staticmethod
    def init_occupant_axes(
        xtal_prim: xtal.Prim,
        sort: bool = True,
        path: Optional[pathlib.Path] = None,
        tol: float = casmglobal.TOL,
    ) -> CompositionAxesType:
        """Initialize with the standard occupant composition axes

        Notes
        -----

        - Occupants which are the same chemistry but different magnetic spin, or
          molecular orientation, etc. are treated as different components.

        Parameters
        ----------
        xtal_prim: libcasm.xtal.Prim
            The prim.
        sort: bool = True
            If `self.components` is None, then `self.calculator` is re-generated.
            By default, components are sorted. If `sort` is False, then the components
            are ordered as found iterating over `Prim.occ_dof`.
        path: Optional[pathlib.Path] = None,
            Path to the axes file, for `load` and `commit`.
        tol: float = libcasm.casmglobal.TOL
            Tolerance for comparison. Used to find composition axes such that the
            parametric composition parameters are non-negative

        """

        components, allowed_occs = make_occupant_components(
            xtal_prim=xtal_prim,
            sort=sort,
        )
        return CompositionAxes.init(
            components=components,
            allowed_occs=allowed_occs,
            path=path,
            tol=tol,
        )

    @staticmethod
    def from_dict(
        data: dict,
        path: Optional[pathlib.Path] = None,
    ) -> CompositionAxesType:
        """Construct CompositionAxes from a dictionary

        Parameters
        ----------
        data: dict
            The dict representation of CompositionAxes
        path: Optional[pathlib.Path] = None
            Path to the axes file, for `load` and `commit`.
        """
        value = CompositionAxes(path=path)
        value._assign_from_dict(data)
        return value

    def to_dict(
        self,
    ) -> dict:
        """Represent CompositionAxes as a Python dict

        The `Composition Axes reference <https://prisms-center.github.io/CASMcode_docs/formats/casm/clex/CompositionAxes/>`_
        documents the format.
        """
        return {
            "current_axes": self.current_axes,
            "enumerated": self.enumerated,
            "possible_axes": {
                key: value.to_dict() for key, value in self.possible_axes.items()
            },
            "components": self.components,
            "allowed_occs": self.allowed_occs,
        }
