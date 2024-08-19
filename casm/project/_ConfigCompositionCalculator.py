from typing import Optional

from libcasm.composition import (
    CompositionCalculator,
    CompositionConverter,
)
from libcasm.configuration import (
    Configuration,
)


class ConfigCompositionCalculator:
    """Calculates configuration compositions"""

    def __init__(
        self,
        calculator: CompositionCalculator,
        converter: Optional[CompositionConverter] = None,
    ):
        R"""
        .. rubric:: Constructor

        Parameters
        ----------
        calculator: libcasm.composition.CompositionCalculator
            A :class:`~libcasm.composition.CompositionCalculator`, used to calculate the
            composition of configurations. This defines the order of and meaning of
            components in the composition per unitcell vector, :math:`\vec{n}`.

        converter: Optional[libcasm.composition.CompositionConverter] = None
            A :class:`~libcasm.composition.CompositionConverter`, which converts the
            composition per unitcell vector, :math:`\vec{n}`, to a parametric
            composition, :math:`\vec{x}`, in terms of user chosen parametric
            composition axes.

        """
        self._calculator = calculator
        self._converter = converter

    @property
    def calculator(self):
        """libcasm.composition.CompositionCalculator: Composition calculator"""
        return self._calculator

    @property
    def components(self):
        """List[str]: Order of component names in results"""
        return self._calculator.components()

    @property
    def converter(self):
        """Optional[libcasm.composition.CompositionConverter]: Composition converter
        (parametric composition axes)"""
        return self._converter

    def per_unitcell(
        self,
        config: Configuration,
        sublattice_index: Optional[int] = None,
    ):
        R"""Configuration composition as number per primitive cell

        Parameters
        ----------
        config : libcasm.configuration.Configuration
            The configuration.
        sublattice_index : Optional[int] = None
            If not None, returns the composition on the specified sublattice in
            range [0, n_sublattice).

        Returns
        -------
        comp_n: numpy.ndarray[numpy.float64[n_components, 1]]
            The composition of each component, as number per primitive cell,
            :math:`\vec{n}`.
        """
        return self._calculator.mean_num_each_component(
            occupation=config.occupation,
            sublattice_index=sublattice_index,
        )

    def per_supercell(
        self,
        config: Configuration,
        sublattice_index: Optional[int] = None,
    ):
        """Configuration composition as number per supercell

        Parameters
        ----------
        config : libcasm.configuration.Configuration
            The configuration.
        sublattice_index : Optional[int] = None
            If not None, returns the composition on the specified sublattice in
            range [0, n_sublattice).

        Returns
        -------
        total_n: numpy.ndarray[numpy.int64[n_components, 1]]
            The total number of each component.
        """
        return self._calculator.num_each_component(
            occupation=config.occupation,
            sublattice_index=sublattice_index,
        )

    def species_frac(
        self,
        config: Configuration,
        sublattice_index: Optional[int] = None,
    ):
        """Configuration composition as species fraction, with [Va] = 0.0

        Parameters
        ----------
        config : libcasm.configuration.Configuration
            The configuration.
        sublattice_index : Optional[int] = None
            If not None, returns the composition on the specified sublattice in
            range [0, n_sublattice).

        Returns
        -------
        species_frac: numpy.ndarray[numpy.float64[n_components, 1]]
            Composition as species fraction, with [Va] = 0.0.
        """

        return self._calculator.species_frac(
            occupation=config.occupation,
            sublattice_index=sublattice_index,
        )

    def param_composition(
        self,
        config: Configuration,
    ):
        R"""Configuration composition, as parametric composition

        Parameters
        ----------
        config : libcasm.configuration.Configuration
            The configuration.

        Returns
        -------
        param_composition: numpy.ndarray[numpy.float64[n_components, 1]]
            The composition of each component, as number per primitive cell,
            converted to parametric composition, :math:`\vec{x}`.
        """
        if self._converter is None:
            raise Exception(
                "Error in ConfigCompositionCalculator: "
                "no composition converter (parametric composition axes)"
            )
        return self._converter.param_composition(
            self.per_unitcell(config),
        )
