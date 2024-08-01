import numpy as np
import libcasm.xtal as xtal
import libcasm.clexulator as clex
import libcasm.configuration as casmconfig


class FittingData:
    """A class that holds all the config_props

    How do we interface this with Project?
    Use prim, config_props, clexulator_source and all from Project class?

    It also gives easy access to querying correlations,
    composition, energy etc.
    """

    def __init__(self, prim: dict, config_props: list):

        # prim of the project
        self.prim = casmconfig.Prim(xtal.Prim.from_dict(prim))

        # supercell_set of the project
        self.supercell_set = casmconfig.SupercellSet(self.prim)

        # store all config_props?
        # do we just extract all the results of
        # config_props like ConfigurationWithProperties and StructureMappingResults
        # and store them separately?
        self.config_props = config_props

        # store all the ConfigurationWithProperties by extracting
        # them from config_props
        self.configurations = [
            casmconfig.ConfigurationWithProperties.from_dict(
                config["configuration_with_properties"], self.supercell_set
            )
            for config in config_props
        ]

        # clexulator of the project
        self.clexulator = None

        # prim neighbor list
        self.prim_neighbor_list = None

    def set_clexulator(self, clexulator_source, **kwargs) -> None:
        """Set clexulator

        Parameters
        ----------
        clexulator_source : TODO
        **kwargs : TODO
        prim_neighbor_list : TODO, optional

        Returns
        -------
        TODO

        """
        if self.prim_neighbor_list is None:
            self.prim_neighbor_list = clex.PrimNeighborList()
        self.clexulator = clex.make_clexulator(
            clexulator_source, self.prim_neighbor_list, **kwargs
        )

    def get_all_correlations_per_unitcell(self):
        """Return correlations per unitcell for all configurations

        Returns
        -------
        np.ndarray
            A matrix where each row corresponds to correlations
            of one configuration

        """
        if self.clexulator is None:
            raise RuntimeError(
                "Please set clexulator first before querying Correlations"
            )

        all_correlations_per_unit_cell = []

        # for every configuration; get correlations per_unitcell
        for config in self.configurations:
            transformation_matrix_to_super = (
                config.configuration.supercell.transformation_matrix_to_super
            )
            super_neighbor_list = clex.SuperNeighborList(
                transformation_matrix_to_super=transformation_matrix_to_super,
                prim_neighbor_list=self.prim_neighbor_list,
            )
            correlations = clex.Correlations(
                super_neighbor_list, self.clexulator, config.configuration.dof_values
            )
            all_correlations_per_unit_cell.append(correlations.per_unitcell())

        return np.array(all_correlations_per_unit_cell)

    def get_energies(self, arg1):
        """TODO: Docstring for get_energies.

        Parameters
        ----------
        arg1 : TODO

        Returns
        -------
        TODO

        """
        pass

    def get_formation_energies(self, arg1):
        """TODO: Docstring for get_formation_energies.

        Parameters
        ----------
        arg1 : TODO

        Returns
        -------
        TODO

        """
        pass

    def get_compositions(self, arg1):
        """TODO: Docstring for get_compositions.

        Parameters
        ----------
        arg1 : TODO

        Returns
        -------
        TODO

        """
        pass
