import numpy as np
import libcasm.xtal as xtal
import libcasm.clexulator as clex
import libcasm.composition as comp
import libcasm.configuration as casmconfig


class FittingData:
    """A convenient class that holds all the required properties
    of configurations which can be used while fitting cluster expansions

    This class can be constructed from :func:`make_calculated_fitting_data` or
    :func:`make_uncalculated_fitting_data`

    If it is constructed from :func:`make_calculated_fitting_data`, all the
    attributes will be filled

    If it is constructed from :func:`make_uncalculated_fitting_data`, all the
    attributes except `formation_energies` will be filled
    """

    def __init__(self):
        """
        Attributes
        ----------
        names : Optional[list[str]] = None
            Names of the configurations
        parametric_compositions : Optional[np.ndarray] = None
            Paramteric compositions of all the configurations
        mol_compositions : Optional[np.ndarray] = None
            Number of components per unitcell of all the configurations
        correlations_per_unitcell : Optional[np.ndarray] = None
            Correlations per unitcell of all the configurations
        formation_energies : Optional[np.ndarray] = None
            Formation energy per unitcell of all the configurations
        """

        self.names = None
        self.parametric_compositions = None
        self.mol_compositions = None
        self.correlations_per_unitcell = None
        self.formation_energies = None

    @staticmethod
    def from_dict(data):
        """Construct FittingData from a dictionary

        Parameters
        ----------
        data : dict
            A dictionary containing `names`, `parametric_compositions`
            `mol_compositions`, `correlations_per_unitcell` and `formation_energies`
            of the configurations
            Note that `formation_energies` can be None

        Returns
        -------
        fitting_data : FittingData
            :class:`FittingData` with `names`, `parametric_compositions`,
            `mol_compositions`, `correlations_per_unitcell` and `formation_energies`
            filled in for all the configurations


        """
        fitting_data = FittingData()

        fitting_data.names = data["names"]
        fitting_data.parametric_compositions = np.array(data["parametric_compositions"])
        fitting_data.mol_compositions = np.array(data["mol_compositions"])
        fitting_data.correlations_per_unitcell = np.array(
            data["correlations_per_unitcell"]
        )
        fitting_data.formation_energies = np.array(data["formation_energies"])

        return fitting_data

    def to_dict(self):
        """Turn `FittingData` into a dictionary with `names`,
        `parametric_compositions`, `mol_compositions`, `correlations_per_unitcell`
        and `formation_energies` for the configurations.

        Returns
        -------
        data : dict

        """

        return dict(
            names=self.names,
            parametric_compositions=self.parametric_compositions.tolist(),
            mol_compositions=self.mol_compositions.tolist(),
            correlations_per_unitcell=self.correlations_per_unitcell.tolist(),
            formation_energies=self.formation_energies.tolist(),
        )


def _extract_correlations_for_configuration(
    configuration: casmconfig.Configuration,
    clexulator: clex.Clexulator,
    prim_neighbor_list: clex.PrimNeighborList,
) -> np.ndarray:
    """Helper function which calculates correlations_per_unitcell
    of a configuration given a clexulator

    Parameters
    ----------
    configuration : libcasm.configuration.Configuration
        :class:`~libcasm.configuration.Configuration` for which to obtain
        correlations
    clexulator : libcasm.clexulator.Clexulator
        :class:`~libcasm.clexulator.Clexulator` which will be used to
        obtain correlations
    prim_neighbor_list : libcasm.clexulator.PrimNeighborList
        A :class:`~libcasm.clexulator.PrimNeighborList` which will be
        used to construct the :class:`~libcasm.clexulator.SuperNeighborList`
        for every configuration and will be used while obtaining correlations

    Returns
    -------
    corr_per_unitcell : np.ndarray
        Correlations per unitcell

    """
    transformation_matrix_to_super = (
        configuration.supercell.transformation_matrix_to_super
    )
    super_neighbor_list = clex.SuperNeighborList(
        transformation_matrix_to_super=transformation_matrix_to_super,
        prim_neighbor_list=prim_neighbor_list,
    )
    corr = clex.Correlations(
        super_neighbor_list,
        clexulator,
        configuration.dof_values,
    )
    return corr.per_unitcell(corr.per_supercell())


def _extract_mol_and_param_comp_for_configuration(
    configuration: casmconfig.Configuration,
    xtal_prim: xtal.Prim,
    composition_converter: comp.CompositionConverter,
):
    """Helper function that calculates mol and parametric
    composition given a configuration

    Parameters
    ----------
    configuration : libcasm.configuration.Configuration
        :class:`~libcasm.configuration.Configuration` for which to obtain
        correlations
    xtal_prim : libcasm.xtal.Prim
        Prim of the project
    composition_converter : libcasm.composition.CompositionConverter
        A :class:`~libcasm.composition.CompositionCalculator` object with
        the warranted composition axes set, which will be used to obtain
        mol and parametric compostions

    Returns
    -------
    mol_comp, param_comp : tuple[np.ndarray, np.ndarray]
        mol composition and parametric composition of the configuration

    """
    # Extract mol compositions-----------
    composition_calculator = comp.CompositionCalculator(
        allowed_occs=xtal_prim.occ_dof(),
        components=composition_converter.components(),
    )
    mol_comp = composition_calculator.mean_num_each_component(configuration.occupation)
    # Convert mol comp to param comp
    param_comp = composition_converter.param_composition(mol_comp)

    return mol_comp, param_comp


def make_calculated_fitting_data(
    xtal_prim: xtal.Prim,
    config_props: list[dict],
    composition_converter: comp.CompositionConverter,
    clexulator: clex.Clexulator,
    prim_neighbor_list: clex.PrimNeighborList,
) -> FittingData:
    """For a given `config_props` list, constructs FittingData which
    which holds compositions, correlations per unitcell, formation energies
    of all the configurations in the `config_props`

    This should be used on `config_props` which is generated by mapping/importing

    Parameters
    ----------
    xtal_prim : xtal.Prim
        Prim of the project
    config_props : list[dict]
        A list containing results of mapping/import
    composition_converter : libcasm.composition.CompositionConverter
        A :class:`~libcasm.composition.CompositionConverter` object with
        the warranted composition axes set, which will be used to obtain
        mol and parametric compostions
    clexulator : libcasm.clexulator.Clexulator
        :class:`~libcasm.clexulator.Clexulator` which will be used to
        obtain correlations
    prim_neighbor_list : libcasm.clexulator.PrimNeighborList
        A :class:`~libcasm.clexulator.PrimNeighborList` which will be
        used to construct the :class:`~libcasm.clexulator.SuperNeighborList`
        for every configuration and will be used while obtaining correlations

    Returns
    -------
    FittingData

    """

    names = []
    parametric_compositions = []
    mol_compositions = []
    correlations_per_unitcell = []
    formation_energies = []

    supercell_set = casmconfig.SupercellSet(casmconfig.Prim(xtal_prim))
    for config_id, config_prop in enumerate(config_props):
        config_with_properties = casmconfig.ConfigurationWithProperties.from_dict(
            config_prop["configuration_with_properties"], supercell_set
        )
        # Extract correlations
        corr_per_unitcell = _extract_correlations_for_configuration(
            configuration=config_with_properties.configuration,
            clexulator=clexulator,
            prim_neighbor_list=prim_neighbor_list,
        )

        # Extract mol and param compositions
        mol_comp, param_comp = _extract_mol_and_param_comp_for_configuration(
            configuration=config_with_properties.configuration,
            xtal_prim=xtal_prim,
            composition_converter=composition_converter,
        )

        names.append("config." + str(config_id))
        correlations_per_unitcell.append(corr_per_unitcell.tolist())
        mol_compositions.append(mol_comp.tolist())
        parametric_compositions.append(param_comp.tolist())

        # This currently assumes that formation energies are already
        # in config props. Should it be like this??
        formation_energies.append(config_prop["formation_energy"])

    fitting_data = FittingData()
    fitting_data.names = names
    fitting_data.correlations_per_unitcell = np.array(correlations_per_unitcell)
    fitting_data.mol_compositions = np.array(mol_compositions)
    fitting_data.parametric_compositions = np.array(parametric_compositions)
    fitting_data.formation_energies = np.array(formation_energies)

    return fitting_data


def make_uncalculated_fitting_data(
    xtal_prim: xtal.Prim,
    config_list: list[dict],
    composition_converter: comp.CompositionConverter,
    clexulator: clex.Clexulator,
    prim_neighbor_list: clex.PrimNeighborList,
) -> FittingData:
    """For a given `config_list` list, constructs FittingData which
    which holds compositions, correlations per unitcell of all the configurations
    in the `config_list`

    This should be used on `config_list` which is generated by enumeration

    Parameters
    ----------
    xtal_prim : xtal.Prim
        Prim of the project
    config_props : list[dict]
        A list containing results of mapping/import
    composition_converter : libcasm.composition.CompositionCalculator
        A :class:`~libcasm.composition.CompositionCalculator` object with
        the warranted composition axes set, which will be used to obtain
        mol and parametric compostions
    clexulator : libcasm.clexulator.Clexulator
        :class:`~libcasm.clexulator.Clexulator` which will be used to
        obtain correlations
    prim_neighbor_list : libcasm.clexulator.PrimNeighborList
        A :class:`~libcasm.clexulator.PrimNeighborList` which will be
        used to construct the :class:`~libcasm.clexulator.SuperNeighborList`
        for every configuration and will be used while obtaining correlations

    Returns
    -------
    FittingData

    """
    names = []
    parametric_compositions = []
    mol_compositions = []
    correlations_per_unitcell = []

    supercell_set = casmconfig.SupercellSet(casmconfig.Prim(xtal_prim))
    for config_id, config in enumerate(config_list):

        config_with_properties = casmconfig.Configuration.from_dict(
            config["configuration_with_properties"], supercell_set
        )

        # Extract correlations
        corr_per_unitcell = _extract_correlations_for_configuration(
            configuration=config_with_properties.configuration,
            clexulator=clexulator,
            prim_neighbor_list=prim_neighbor_list,
        )

        # Extract mol and param compositions
        mol_comp, param_comp = _extract_mol_and_param_comp_for_configuration(
            configuration=config_with_properties.configuration,
            xtal_prim=xtal_prim,
            composition_converter=composition_converter,
        )

        names.append("config." + str(config_id))
        correlations_per_unitcell.append(corr_per_unitcell)
        mol_compositions.append(mol_comp)
        parametric_compositions.append(param_comp)

    fitting_data = FittingData()
    fitting_data.names = names
    fitting_data.correlations_per_unitcell = correlations_per_unitcell
    fitting_data.mol_compositions = mol_compositions
    fitting_data.parametric_compositions = parametric_compositions

    return fitting_data
