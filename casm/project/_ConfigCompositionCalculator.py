from typing import Any, Optional

import numpy as np

from libcasm.composition import (
    CompositionCalculator,
    CompositionConverter,
    make_chemical_subsystems,
)
from libcasm.configuration import (
    Configuration,
    ConfigurationRecord,
    ConfigurationWithProperties,
)


def _independent_compositions(
    components: list[str],
    allowed_occs: list[list[str]],
):
    chemical_subsystems, _, _ = make_chemical_subsystems(
        components=components,
        allowed_occs=allowed_occs,
    )

    k = 0
    for subsystem in chemical_subsystems:
        k += len(subsystem) - 1
    return k


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

        if self._converter is not None:
            if self._calculator.components() != self._calculator.components():
                raise Exception(
                    "Error in ConfigCompositionCalculator: inconsistent components"
                )
            self.independent_compositions = self._converter.independent_compositions()
        else:
            self.independent_compositions = _independent_compositions(
                components=self._calculator.components(),
                allowed_occs=self._calculator.allowed_occs(),
            )

    @property
    def calculator(self):
        """libcasm.composition.CompositionCalculator: Composition calculator"""
        return self._calculator

    @property
    def components(self):
        """List[str]: Order of component names in results"""
        return self._calculator.components()

    @property
    def n_components(self):
        """int: Number components in results"""
        return len(self._calculator.components())

    @property
    def converter(self):
        """Optional[libcasm.composition.CompositionConverter]: Composition converter
        (parametric composition axes)"""
        return self._converter

    def per_unitcell(
        self,
        x: Any,
        sublattice_index: Optional[int] = None,
    ):
        R"""Configuration composition as number per primitive cell

        Parameters
        ----------
        x : Any
            May be a Configuration, ConfigurationWithProperties, ConfigurationRecord,
            or an iterable of these.
        sublattice_index : Optional[int] = None
            If not None, returns the composition on the specified sublattice in
            range [0, n_sublattice).

        Returns
        -------
        comp_n: numpy.ndarray
            The composition of each component, as number per primitive cell,
            :math:`\vec{n}`. If the input `x` is a single Configuration, the output is
            a 1d array with shape=(n_components,). If the input is an iterable, the
            output is a 2d array with shape=(n_config, n_components).
        """
        if isinstance(x, Configuration):
            config = x
        elif isinstance(x, (ConfigurationWithProperties, ConfigurationRecord)):
            config = x.configuration
        else:
            return np.vstack(
                [self.per_unitcell(xi, sublattice_index=sublattice_index) for xi in x],
            )
        return self._calculator.mean_num_each_component(
            occupation=config.occupation,
            sublattice_index=sublattice_index,
        )

    def per_supercell(
        self,
        x: Any,
        sublattice_index: Optional[int] = None,
    ):
        R"""Configuration composition as number per supercell

        Parameters
        ----------
        x : Any
            May be a Configuration, ConfigurationWithProperties, ConfigurationRecord,
            or an iterable of these.
        sublattice_index : Optional[int] = None
            If not None, returns the composition on the specified sublattice in
            range [0, n_sublattice).

        Returns
        -------
        total_n: numpy.ndarray
            The number of each component, as number per primitive cell, :math:`\vec{N}`.
            If the input `x` is a single Configuration, the output is a 1d array with
            shape=(n_components,). If the input is a container of Configuration, the
            output is a 2d array with shape=(n_config, n_components).
        """
        if isinstance(x, Configuration):
            config = x
        elif isinstance(x, (ConfigurationWithProperties, ConfigurationRecord)):
            config = x.configuration
        else:
            return np.vstack(
                [self.per_supercell(xi, sublattice_index=sublattice_index) for xi in x],
                dtype=int,
            )
        return self._calculator.num_each_component(
            occupation=config.occupation,
            sublattice_index=sublattice_index,
        )

    def species_frac(
        self,
        x: Any,
        sublattice_index: Optional[int] = None,
    ):
        """Configuration composition as species fraction, with [Va] = 0.0

        Parameters
        ----------
        x : Any
            May be a Configuration, ConfigurationWithProperties, ConfigurationRecord,
            or an iterable of these.
        sublattice_index : Optional[int] = None
            If not None, returns the composition on the specified sublattice in
            range [0, n_sublattice).

        Returns
        -------
        species_frac: numpy.ndarray
            Composition as species fraction, with [Va] = 0.0. If the input `x` is
            a single Configuration, the output is a 1d array with shape=(n_components,).
            If the input is a container of Configuration, the output is a 2d array with
            shape=(n_config, n_components).
        """
        if isinstance(x, Configuration):
            config = x
        elif isinstance(x, (ConfigurationWithProperties, ConfigurationRecord)):
            config = x.configuration
        else:
            return np.vstack(
                [self.species_frac(xi, sublattice_index=sublattice_index) for xi in x]
            )
        return self._calculator.species_frac(
            occupation=config.occupation,
            sublattice_index=sublattice_index,
        )

    def param_composition(
        self,
        x: Any,
    ):
        R"""Configuration composition, as parametric composition

        Parameters
        ----------
        x : Any
            May be a Configuration, ConfigurationWithProperties, ConfigurationRecord,
            or an iterable of these.

        Returns
        -------
        param_composition: numpy.ndarray
            The composition of each component, as number per primitive cell,
            converted to parametric composition, :math:`\vec{x}`. If the input `x` is
            a single Configuration, the output is a 1d array with shape=(k,).
            If the input is an iterable, the output is a 2d array with
            shape=(n_config, k), where `k` is the number of independent composition
            axes.
        """
        if self._converter is None:
            raise Exception(
                "Error in ConfigCompositionCalculator.param_composition: "
                "no composition converter (parametric composition axes)"
            )
        if isinstance(x, Configuration):
            config = x
        elif isinstance(x, (ConfigurationWithProperties, ConfigurationRecord)):
            config = x.configuration
        else:
            return np.vstack([self.param_composition(xi) for xi in x])
        return self._converter.param_composition(
            self.per_unitcell(config),
        )
