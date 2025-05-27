from typing import Any, Optional

import numpy as np

from libcasm.clexulator import (
    Clexulator,
    Correlations,
    PrimNeighborList,
    SuperNeighborList,
)
from libcasm.configuration import (
    Configuration,
    ConfigurationRecord,
    ConfigurationWithProperties,
)


class ConfigCorrCalculator:
    """Calculate correlations for configurations"""

    def __init__(
        self,
        clexulator: Clexulator,
        prim_neighbor_list: PrimNeighborList,
        linear_function_indices: Optional[list[int]] = None,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        clexulator: libcasm.clexulator.Clexulator
            The :class:`~libcasm.clexulator.Clexulator` used to calculate basis
            functions.
        prim_neighbor_list: libcasm.clexulator.PrimNeighbList
            The :class:`~libcasm.clexulator.PrimNeighborList` used to construct
            supercell neighbor lists. Must be consistent with `clexulator`.
        linear_function_indices: Optional[list[int]] = None
            If provided, only calculate the basis functions with corresponding indices.
            The same size correlation array is always returned, but other values will
            be of undefined value.
        """

        if not isinstance(clexulator, Clexulator):
            raise TypeError(f"clexulator must be a Clexulator, not {type(clexulator)}")
        self._clexulator = clexulator
        """libcasm.clexulator.Clexulator: The :class:`~libcasm.clexulator.Clexulator` 
        used to calculate basis functions."""

        if not isinstance(prim_neighbor_list, PrimNeighborList):
            raise TypeError(
                f"prim_neighbor_list must be a PrimNeighborList, "
                f"not {type(prim_neighbor_list)}"
            )
        self._prim_neighbor_list = prim_neighbor_list
        """libcasm.clexulator.PrimNeighborList: The PrimNeighborList used to construct
        the supercell neighbor lists."""

        self._linear_function_indices = linear_function_indices
        """Optional[list[int]]: If provided, only calculate the basis functions with 
        corresponding indices.
            
        The same size correlation array is always returned, but other values will
        be of undefined value."""

        self._supercell = None
        """libcasm.configuration.Supercell: Supercell for which `self._corr_calculator`
        is constructed to calculate correlations."""

        self._supercell_neighbor_list = None
        """libcasm.clexulator.SuperNeighborList: Supercell neighbor list for 
        `self._supercell`."""

        self._corr_calculator = None
        """libcasm.clexulator.Correlations: The Correlations calculator."""

    def _get(self, config: Configuration) -> Correlations:
        # handles constructing the supercell neighbor list and Correlations calculator
        if self._supercell is not config.supercell:
            self._supercell = config.supercell
            self._supercell_neighbor_list = SuperNeighborList(
                transformation_matrix_to_super=self._supercell.transformation_matrix_to_super,
                prim_neighbor_list=self._prim_neighbor_list,
            )
            self._corr_calculator = Correlations(
                supercell_neighbor_list=self._supercell_neighbor_list,
                clexulator=self._clexulator,
                config_dof_values=config.dof_values,
                indices=self._linear_function_indices,
            )
        self._corr_calculator.set(config.dof_values)
        return self._corr_calculator

    def corr_f(self, config: Configuration) -> Correlations:
        """Return a :class:`~libcasm.clexulator.Correlations` calculator instance for a
        particular configuration."""
        return self._get(config)

    @property
    def n_functions(self):
        """Return the number of basis functions

        Returns
        -------
        n_functions: int
            The number of basis functions.
        """
        return self._clexulator.n_functions()

    @property
    def n_point_corr(self):
        """Return the number of point correlations that can be calculated

        Returns
        -------
        n_point_corr: int
            The number of point cluster correlations.
        """
        return self._clexulator.n_point_corr()

    @property
    def linear_function_indices(self):
        return self._linear_function_indices

    def per_supercell(self, x: Any):
        """Calculate and return correlations for a configuration, normalized
        per supercell

        Parameters
        ----------
        x : Any
            May be a Configuration, ConfigurationWithProperties, ConfigurationRecord,
            or an iterable of these.

        Returns
        -------
        corr: numpy.ndarray
            The correlations, normalized per supercell. If the input `x` is a single
            Configuration, the output is a 1d array with shape=(n_functions,). If the
            input is an iterable, the output is a 2d array with
            shape=(n_config, n_functions).

        """
        if isinstance(x, Configuration):
            config = x
        elif isinstance(x, (ConfigurationWithProperties, ConfigurationRecord)):
            config = x.configuration
        else:
            return np.vstack(
                [self.per_supercell(xi) for xi in x],
            )
        return self._get(config).per_supercell().copy()

    def per_unitcell(
        self,
        x: Any,
    ):
        """Calculate and return correlations

        Parameters
        ----------
        x : Any
            May be a Configuration, ConfigurationWithProperties, ConfigurationRecord,
            or an iterable of these.

        Returns
        -------
        corr: numpy.ndarray
            The correlations, normalized per unitcell. If the input `x` is a single
            Configuration, the output is a 1d array with shape=(n_functions,). If the
            input is an iterable, the output is a 2d array with
            shape=(n_config, n_functions).

        """
        if isinstance(x, Configuration):
            config = x
        elif isinstance(x, (ConfigurationWithProperties, ConfigurationRecord)):
            config = x.configuration
        else:
            return np.vstack(
                [self.per_unitcell(xi) for xi in x],
            )
        corr_calculator = self._get(config)
        return corr_calculator.per_unitcell(corr_calculator.per_supercell()).copy()

    def all_points(
        self,
        config: Configuration,
        include_all_sites: bool = True,
    ):
        """Calculate and return all point correlations, as a matrix

        Parameters
        ----------
        config: libcasm.configuration.Configuration
            A Configuration
        include_all_sites: bool = True
            If true, include a row for every site, even if there are no point
            correlations associated with that site (in which case the row is all zeros).
            If false, rows are only included for sites from sublattices included in the
            prim neighbor list (rows are still ordered according to increasing site
            index).

        Returns
        -------
        all_points: numpy.ndarray[numpy.float64[n_sites, n_functions]]
            All point correlations, as rows of a matrix.

        """
        return self._get(config).all_points(include_all_sites=include_all_sites).copy()

    def all_points_site_indices(
        self,
        config: Configuration,
        include_all_sites: bool = True,
    ) -> list[int]:
        """Return the site index corresponding to each row of the matrix returned by
        `all_points`

        Parameters
        ----------
        config: libcasm.configuration.Configuration
            A Configuration
        include_all_sites: bool = True
            If true, include a row for every site, even if there are no point
            correlations associated with that site (in which case the row is all zeros).
            If false, rows are only included for sites from sublattices included in the
            prim neighbor list (rows are still ordered according to increasing site
            index).

        Returns
        -------
        site_indices: list[int]
            The site index corresponding to each row of the matrix returned by
            all_points.

        """
        return self._get(config).all_points_site_indices(
            include_all_sites=include_all_sites
        )
