from typing import Any, Optional, TypeVar

import libcasm.casmglobal as casmglobal
import libcasm.xtal as xtal
from libcasm.composition import (
    CompositionCalculator,
    CompositionConverter,
    make_standard_origin_and_end_members,
)

from ._ConfigCompositionCalculator import ConfigCompositionCalculator


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
    (components, allowed_occs):

        components: list[str],
            The requested component order in the composition vectors. Occupants
            are distinguished by `Occupant.name` (the chemical name). The components
            are ordered as found iterating over `Prim.occ_dof`.

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
    (components, allowed_occs):

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
    (calculator, standard_axes):

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


def axes_from_dict(cls: Any, data: dict) -> Any:
    value = cls()
    value.allowed_occs = data["allowed_occs"]
    value.components = data["components"]
    value.enumerated = data["enumerated"]
    value.possible_axes = {
        key: CompositionConverter.from_dict(value)
        for key, value in data["possible_axes"].items()
    }
    value.current_axes = data["current_axes"]
    value.calculator = CompositionCalculator(
        components=value.components,
        allowed_occs=value.allowed_occs,
    )
    return value


def axes_to_dict(axes: Any) -> dict:
    return {
        "current_axes": axes.current_axes,
        "enumerated": axes.enumerated,
        "possible_axes": {
            key: value.to_dict() for key, value in axes.possible_axes.items()
        },
        "components": axes.components,
        "allowed_occs": axes.allowed_occs,
    }


ChemicalCompositionAxesType = TypeVar("ChemicalCompositionAxesType")


class ChemicalCompositionAxes:
    """Chemical composition axes

    This class is used to:

    - make a :class:`~libcasm.composition.CompositionCalculator`
    - make and store a list of :class:`~libcasm.composition.CompositionConverter` in
      which occupants which have the same chemical name are treated as a single
      component, even if they have different magnetic spin, or molecular orientation,
      etc.
    - store which :class:`~libcasm.composition.CompositionConverter` is the default
      axes choice.

    """

    def __init__(self):
        """
        .. rubric:: Constructor

        Notes
        -----

        It is expected that ChemicalCompositionAxes is constructed using one of:

        - :func:`~casm.project.ChemicalCompositionAxes.init`
        - :func:`~casm.project.ChemicalCompositionAxes.from_dict`

        """

        self.components = None
        """Optional[list[str]]: The component order in the composition vectors.
        
        A user may customize the order of components in this list to adjust the order
        of components in the calculated composition vectors.
        """

        self.allowed_occs: Optional[list[list[str]]] = None
        """Optional[list[list[str]]]: For each sublattice, a vector of components \
        allowed to occupy the sublattice.
        
        The values must be elements in `components`. The order must be consistent 
        with the order of occupants listed in `xtal.Prim.occ_dof`. This should be 
        used as calculated.
        """

        self.calculator = None
        """Optional[CompositionCalculator]: Composition calculator"""

        self.enumerated: list[str] = []
        """list[str]: Keys of enumerated standard axes"""

        self.possible_axes: dict[str, CompositionConverter] = {}
        """dict[str, CompositionConverter]: All possible axes, enumerated and custom, \
        by id string"""

        self.current_axes: Optional[str] = None
        """Optional[str]: Key of current axes in `self.possible_axes`"""

    @property
    def config_composition(self) -> ConfigCompositionCalculator:
        return ConfigCompositionCalculator(
            calculator=self.calculator,
            converter=self.possible_axes.get(self.current_axes),
        )

    @staticmethod
    def init(
        xtal_prim: xtal.Prim,
        sort: bool = True,
        tol: float = casmglobal.TOL,
    ) -> ChemicalCompositionAxesType:
        """Initialize with the standard chemical composition axes

        Notes
        -----

        - Generates or overwrites the enumerated standard composition axes.
        - Keeps any custom axes.

        """

        value = ChemicalCompositionAxes()
        value.calculate(
            xtal_prim=xtal_prim,
            sort=sort,
            tol=tol,
        )
        return value

    def calculate(
        self,
        xtal_prim: xtal.Prim,
        sort: bool = True,
        tol: float = casmglobal.TOL,
    ):
        """Calculate (or re-calculate) the standard composition axes

        Notes
        -----

        - Generates or overwrites the enumerated standard composition axes.
        - Keeps any custom axes.

        """
        for key in self.enumerated:
            if key in self.possible_axes:
                del self.possible_axes[key]

        components, self.allowed_occs = make_chemical_components(
            xtal_prim=xtal_prim,
            sort=sort,
        )

        if self.components is None:
            self.components = components

        calculator, enumerated_axes = make_standard_axes(
            components=self.components,
            allowed_occs=self.allowed_occs,
            tol=tol,
        )

    @staticmethod
    def from_dict(
        data: dict,
    ) -> ChemicalCompositionAxesType:
        """Construct ChemicalCompositionAxesType from a dictionary"""
        return axes_from_dict(ChemicalCompositionAxes, data)

    def to_dict(
        self,
    ) -> dict:
        """Represent ChemicalCompositionAxes as a Python dict

        The `Composition Axes reference <https://prisms-center.github.io/CASMcode_docs/formats/casm/clex/CompositionAxes/>`_
        documents the format.
        """
        return axes_to_dict(self)


OccupantCompositionAxesType = TypeVar("OccupantCompositionAxesType")


class OccupantCompositionAxes:
    """Unique occupant composition axes

    This class is used to:

    - make a :class:`~libcasm.composition.CompositionCalculator`
    - make and store a list of :class:`~libcasm.composition.CompositionConverter` in
      which occupants which are the same chemistry but different magnetic spin, or
      molecular orientation, etc. are treated as different components.
    - store which :class:`~libcasm.composition.CompositionConverter` is the default
      axes choice.

    """

    def __init__(self):
        """
        .. rubric:: Constructor

        Notes
        -----

        It is expected that OccupantCompositionAxes is constructed using one of:

        - :func:`~casm.project.OccupantCompositionAxes.init`
        - :func:`~casm.project.OccupantCompositionAxes.from_dict`

        """

        self.components = None
        """Optional[list[str]]: The component order in the composition vectors.

        A user may customize the order of components in this list to adjust the order
        of components in the calculated composition vectors.
        """

        self.allowed_occs: Optional[list[list[str]]] = None
        """Optional[list[list[str]]]: For each sublattice, a vector of components \
        allowed to occupy the sublattice.

        The values must be elements in `components`. The order must be consistent 
        with the order of occupants listed in `xtal.Prim.occ_dof`. This should be 
        used as calculated.
        """

        self.calculator = None
        """Optional[CompositionCalculator]: Composition calculator"""

        self.enumerated: list[str] = []
        """list[str]: Keys of enumerated standard axes
        
        This is populated by the `calculate` method.
        """

        self.possible_axes: dict[str, CompositionConverter] = {}
        """dict[str, CompositionConverter]: All possible axes, enumerated and custom, \
        by id string.
        
        The enumerated axes are constructed by the `calculate` method. The custom
        axes are user provided.
        """

        self.current_axes: Optional[str] = None
        """Optional[str]: Key of current axes in `self.possible_axes`"""

    @property
    def config_composition(self) -> ConfigCompositionCalculator:
        return ConfigCompositionCalculator(
            calculator=self.calculator,
            converter=self.possible_axes.get(self.current_axes),
        )

    @staticmethod
    def init(
        xtal_prim: xtal.Prim,
        sort: bool = True,
        tol: float = casmglobal.TOL,
    ) -> OccupantCompositionAxesType:
        """Initialize with the standard chemical composition axes

        Notes
        -----

        - Generates or overwrites the enumerated standard composition axes.
        - Keeps any custom axes.

        """

        value = OccupantCompositionAxes()
        value.calculate(
            xtal_prim=xtal_prim,
            sort=sort,
            tol=tol,
        )
        return value

    def calculate(
        self,
        xtal_prim: xtal.Prim,
        sort: bool = True,
        tol: float = casmglobal.TOL,
    ):
        """Calculate (or re-calculate) the standard composition axes

        Notes
        -----

        - Generates or overwrites the enumerated standard composition axes.
        - Keeps any custom axes.

        """
        for key in self.enumerated:
            if key in self.possible_axes:
                del self.possible_axes[key]

        components, self.allowed_occs = make_occupant_components(
            xtal_prim=xtal_prim,
            sort=sort,
        )

        if self.components is None:
            self.components = components

        calculator, enumerated_axes = make_standard_axes(
            components=self.components,
            allowed_occs=self.allowed_occs,
            tol=tol,
        )

    @staticmethod
    def from_dict(
        data: dict,
    ) -> OccupantCompositionAxesType:
        """Construct OccupantCompositionAxesType from a dictionary"""
        return axes_from_dict(OccupantCompositionAxes, data)

    def to_dict(
        self,
    ) -> dict:
        """Represent OccupantCompositionAxes as a Python dict

        The `Composition Axes reference <https://prisms-center.github.io/CASMcode_docs/formats/casm/clex/CompositionAxes/>`_
        documents the format.
        """
        return axes_to_dict(self)
