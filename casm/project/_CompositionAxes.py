import pathlib
import sys
from typing import Any, Optional, TextIO, TypeVar, Union

import libcasm.casmglobal as casmglobal
import libcasm.xtal as xtal
from libcasm.composition import (
    CompositionCalculator,
    CompositionConverter,
    make_standard_axes,
    print_axes_summary,
    print_axes_table,
)

from ._ConfigCompositionCalculator import (
    ConfigCompositionCalculator,
    _independent_compositions,
)
from .json_io import (
    read_required,
    safe_dump,
)


def _update_components(
    components: Union[str, list[str], None],
    unique_components: list[str],
) -> list[str]:
    invalid_value_error = ValueError(
        f"Invalid value for `components`: {components}. "
        f"May be None, or a list of "
        f"components, or 'sorted' to sort components alphabetically."
    )

    if components is None:
        return unique_components
    elif isinstance(components, str):
        if components == "sorted":
            return sorted(unique_components)
        else:
            raise invalid_value_error
    elif isinstance(components, list):
        if sorted(components) != sorted(unique_components):
            raise ValueError(
                f"Given `components` ({components}) do not match the components "
                f"found in `allowed_occs`: ({unique_components})"
            )
    else:
        raise invalid_value_error


def _make_chemical_components(
    xtal_prim: xtal.Prim,
    components: Union[str, list[str], None] = None,
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
    components: Union[str, list[str], None] = None
        The requested component order in the composition vectors. If None, the
        components are listed in the order found in `allowed_occs`. If the string
        "sorted", the components are sorted alphabetically. If a list, the components
        are listed in the order given in the list.

    Returns
    -------
    components: list[str],
        The requested component order in the composition vectors. Occupants
        are distinguished by `Occupant.name` (the chemical name).

    allowed_occs: list[list[str]],
        For each sublattice, a vector of components allowed to occupy
        the sublattice.
    """
    unique_components = []
    allowed_occs = []

    occupants = xtal_prim.occupants()
    occ_dof = xtal_prim.occ_dof()
    for site_occ_dof in occ_dof:
        site_allowed_occs = []
        for occ_id in site_occ_dof:
            occupant = occupants[occ_id]
            if occupant.name() not in unique_components:
                unique_components.append(occupant.name())
            site_allowed_occs.append(occupant.name())
        allowed_occs.append(site_allowed_occs)

    components = _update_components(
        components=components,
        unique_components=unique_components,
    )

    return (components, allowed_occs)


def _make_occupant_components(
    xtal_prim: xtal.Prim,
    components: Union[str, list[str], None] = None,
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
    components: Union[str, list[str], None] = None
        The requested component order in the composition vectors. If None, the
        components are listed in the order found in `allowed_occs`. If the string
        "sorted", the components are sorted alphabetically. If a list, the components
        are listed in the order given in the list.


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
    unique_components = []
    allowed_occs = []

    occ_dof = xtal_prim.occ_dof()
    for site_occ_dof in occ_dof:
        site_allowed_occs = []
        for occ_id in site_occ_dof:
            if occ_id not in unique_components:
                unique_components.append(occ_id)
            site_allowed_occs.append(occ_id)
        allowed_occs.append(site_allowed_occs)

    components = _update_components(
        components=components,
        unique_components=unique_components,
    )

    return (components, allowed_occs)


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

        self.allowed_occs = None
        """Optional[list[list[str]]]: For each sublattice, a vector of components \
        allowed to occupy the sublattice.

        The values must be elements in `components`. The order must be consistent 
        with the order of occupants listed in `xtal.Prim.occ_dof`. This should be 
        used as calculated.
        """

        self.calculator = None
        """Optional[CompositionCalculator]: Composition calculator"""

        self.independent_compositions = None
        """Optional[int]: Number independent composition axes, :math:`k`."""

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

        self.include_va: bool = False
        """bool: If True, include "chem_pot(Va)" in formulas; If False (default)
        assume that the vacancy chemical potential is zero."""

    def set_current_axes(self, key: Optional[Any] = None):
        """Select the current composition axes

        Parameters
        ----------
        key: Optional[Any] = None
            The key of one of the `possible_axes` to set as the current axes. If None,
            then the current axes are cleared. If `key` is not found, then a ValueError
            is raised. The key must be a string or convertible to string.
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
        self.enumerated = data["enumerated"]
        self.possible_axes = {
            key: CompositionConverter.from_dict(x)
            for key, x in data["possible_axes"].items()
        }
        self.current_axes = data["current_axes"]
        self.calculator = CompositionCalculator(
            components=data["components"],
            allowed_occs=self.allowed_occs,
        )
        self.include_va = data.get("include_va", False)

        self.independent_compositions = _independent_compositions(
            components=self.calculator.components(),
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

    def set_include_va(self, include_va: bool):
        """Set whether vacancy chemical potential is included in formulas

        Parameters
        ----------
        include_va: Optional[bool] = None
            If True, include the vacancy chemical potential when printing formulas.
            If False, assume that the vacancy chemical potential is zero.
        """
        self.include_va = include_va

    def print_axes_table(
        self,
        out: Optional[TextIO] = None,
    ):
        """Print a formatted summary of possible_axes

        Parameters
        ----------
        out: Optional[TextIO] = None
            Output stream. Defaults to `sys.stdout`
        """
        print_axes_table(
            possible_axes=self.possible_axes,
            out=out,
        )

    def print_current_axes(
        self,
        out: Optional[TextIO] = None,
    ):
        """Print a formatted summary of the formulas for the
        current composition axes

        Parameters
        ----------
        out: Optional[TextIO] = None
            Output stream. Defaults to `sys.stdout`

        """

        if out is None:
            out = sys.stdout
        if self.current_axes is None:
            out.write("No composition axes selected\n")
            return
        if self.current_axes not in self.possible_axes:
            raise ValueError(
                "Error in CompositionAxes.print_current_axes: "
                f"current_axes ('{self.current_axes}') not found in possible_axes"
            )
        out.write(f"Currently selected composition axes: {self.current_axes}\n\n")
        print_axes_summary(
            composition_converter=self.possible_axes.get(self.current_axes),
            include_va=self.include_va,
            out=out,
        )

    def print_axes(
        self,
        key: Optional[Any] = None,
        out: Optional[TextIO] = None,
    ):
        """Print a formatted summary of the composition formulas for a
        particular choice of axes

        Parameters
        ----------
        key: Optional[Any] = None
            The key of one of the `possible_axes` to print. If `key` is not found,
            then a ValueError
            is raised. The key must be a string or convertible to string.
        out: Optional[TextIO] = None
            Output stream. Defaults to `sys.stdout`

        """
        key = str(key)
        if key not in self.possible_axes:
            raise ValueError(
                f"Error in CompositionAxes.print_axes: "
                f"'{key}' not found in possible_axes"
            )
        if out is None:
            out = sys.stdout
        out.write(f"Composition axes: {key}\n\n")
        print_axes_summary(
            composition_converter=self.possible_axes.get(key),
            include_va=self.include_va,
            out=out,
        )

    def __repr__(self):
        from io import StringIO

        out = StringIO()
        self.print_axes_table(out)
        out.write("\n")
        self.print_current_axes(out=out)
        return out.getvalue().strip()

    def make_config_comp_calculator(self) -> ConfigCompositionCalculator:
        """Make a configuration composition calculator using the current axes.

        Returns
        -------
        chemical_comp_calculator: casm.configuration.ConfigCompositionCalculator
            A configuration composition calculator for the chemical composition axes,
            using the currently selected parametric composition axes (may be None).
        """
        converter = None
        if self.current_axes is not None:
            converter = self.possible_axes.get(self.current_axes)
        return ConfigCompositionCalculator(
            calculator=self.calculator,
            converter=converter,
        )

    @staticmethod
    def init(
        allowed_occs: list[list[str]],
        components: Union[str, list[str], None] = None,
        path: Optional[pathlib.Path] = None,
        tol: float = casmglobal.TOL,
    ):
        """Initialize with standard axes

        Parameters
        ----------
        allowed_occs: list[list[str]]
            For each sublattice, a vector of components allowed to occupy the
            sublattice. This must be consistent with the prim.
        components: Union[str, list[str], None] = None
            The requested component order in the composition vectors. If None, the
            components are listed in the order found in `allowed_occs`. If the string
            "sorted", the components are sorted alphabetically. If a list, the
            components are listed in the order given in the list.
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
        value.allowed_occs = allowed_occs
        value.independent_compositions = _independent_compositions(
            components=components,
            allowed_occs=allowed_occs,
        )

        if value.independent_compositions == 0:
            value.calculator = CompositionCalculator(
                components=components,
                allowed_occs=allowed_occs,
            )
            return value

        value.calculator, enumerated_axes = make_standard_axes(
            components=components,
            allowed_occs=allowed_occs,
            normalize=True,
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
        components: Union[str, list[str], None] = None,
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
        components: Union[str, list[str], None] = None
            The requested component order in the composition vectors. If None, the
            components are listed in the order found in `allowed_occs`. If the string
            "sorted", the components are sorted alphabetically. If a list, the
            components are listed in the order given in the list.
        path: Optional[pathlib.Path] = None,
            Path to the axes file, for `load` and `commit`.
        tol: float = libcasm.casmglobal.TOL
            Tolerance for comparison. Used to find composition axes such that the
            parametric composition parameters are non-negative

        """
        components, allowed_occs = _make_chemical_components(
            xtal_prim=xtal_prim,
            components=components,
        )
        return CompositionAxes.init(
            allowed_occs=allowed_occs,
            components=components,
            path=path,
            tol=tol,
        )

    @staticmethod
    def init_occupant_axes(
        xtal_prim: xtal.Prim,
        components: Union[str, list[str], None] = None,
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
        components: Union[str, list[str], None] = None
            The requested component order in the composition vectors. If None, the
            components are listed in the order found in `allowed_occs`. If the string
            "sorted", the components are sorted alphabetically. If a list, the
            components are listed in the order given in the list.
        path: Optional[pathlib.Path] = None,
            Path to the axes file, for `load` and `commit`.
        tol: float = libcasm.casmglobal.TOL
            Tolerance for comparison. Used to find composition axes such that the
            parametric composition parameters are non-negative

        """

        components, allowed_occs = _make_occupant_components(
            xtal_prim=xtal_prim,
            components=components,
        )
        return CompositionAxes.init(
            allowed_occs=allowed_occs,
            components=components,
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
        # TODO: update Composition Axes format with `include_va`
        return {
            "current_axes": self.current_axes,
            "enumerated": self.enumerated,
            "possible_axes": {
                key: value.to_dict() for key, value in self.possible_axes.items()
            },
            "components": self.calculator.components(),
            "allowed_occs": self.allowed_occs,
            "include_va": self.include_va,
        }
