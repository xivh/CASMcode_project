import libcasm.configuration as casmconfig
import libcasm.enumerate as casmenum
import libcasm.mapping.mapsearch as mapsearch
import libcasm.mapping.methods as mapmethods
import libcasm.xtal as xtal


def map_structure(
    parent: xtal.Prim,
    child: xtal.Structure,
    max_vol: int,
    min_vol: int = 1,
    min_cost: float = 0.0,
    max_cost: float = 1e20,
    lattice_cost_weight: float = 0.5,
    lattice_cost_method: str = "isotropic_strain_cost",
    atom_cost_method: str = "isotropic_disp_cost",
    k_best: int = 1,
    cost_tol: float = 1e-05,
):
    """Find structure mappings between a parent and child structure.

    Notes
    -----

    - Parent superstructures (:math:`L1 T`) are canonical supercells, but
      the reorientation matrix, :math:`N`, may not be identity.


    Parameters
    ----------
    parent : xtal.Prim
        The parent crystal structure.
    child : xtal.Structure
        The child crystal structure.
    max_vol : int
        The maximum volume of supercells of the parent to consider mapping the child to.
    min_vol : int = 1
        The minimum volume of supercells of the parent to consider mapping the child
        to, by default 1.
    min_cost: float = 0.0
        The minimum cost of a mapping to consider, by default 0.0.
    max_cost: float = 1e20
        The maximum cost of a mapping to consider, by default 1e20.
    lattice_cost_weight: float = 0.5
        The weight of the lattice cost in the total cost, by default 0.5.
    lattice_cost_method: str = "isotropic_strain_cost"
        The method to use for lattice cost calculation. Must be one of
        "isotropic_strain_cost" or "symmetry_breaking_strain_cost", by default
        "isotropic_strain_cost".
    atom_cost_method: str = "isotropic_disp_cost"
        The method to use for atom cost calculation. Must be one of
        "isotropic_disp_cost" or "symmetry_breaking_disp_cost", by default
        "isotropic_disp_cost".
    k_best: int = 1
        The number of best mappings to return, by default 1. More than `k_best`
        mappings may be returned if there are approximate ties.
    cost_tol: float = 1e-05
        The tolerance for cost comparisons, by default 1e-05.

    Returns
    -------
    structure_mappings: libcasm.mapping.info.StructureMappingResults
        A StructureMappingResults object, giving possible structure mappings, sorted by
        total cost. The ideal structure is guaranteed to be in a canonical supercell.

    """

    # validation
    if lattice_cost_method not in [
        "isotropic_strain_cost",
        "symmetry_breaking_strain_cost",
    ]:
        raise ValueError(
            f"lattice_cost_method must be one of "
            f"'isotropic_strain_cost' or 'symmetry_breaking_strain_cost', "
            f"not '{lattice_cost_method}'"
        )

    if atom_cost_method not in ["isotropic_disp_cost", "symmetry_breaking_disp_cost"]:
        raise ValueError(
            f"atom_cost_method must be one of "
            f"'isotropic_disp_cost' or 'symmetry_breaking_disp_cost', "
            f"not '{atom_cost_method}'"
        )

    # Additional parameters:
    enable_remove_mean_displacement = True
    min_queue_cost = None
    max_queue_cost = max_cost
    max_queue_size = None
    lattice_mapping_min_cost = 0.0
    lattice_mapping_max_cost = max_cost
    lattice_mapping_k_best = k_best
    lattice_mapping_reorientation_range = 1
    lattice_mapping_cost_tol = cost_tol
    infinity = 1e20
    forced_on = {}  # {site_index: atom_index}
    forced_off = []  # [ (site_index, atom_index) ]

    debug = False

    # Create a PrimSearchData object for the parent crystal structure.
    parent_xtal_prim = parent
    parent_prim = casmconfig.Prim(parent_xtal_prim)

    enable_symmetry_breaking_atom_cost = False
    if atom_cost_method == "symmetry_breaking_disp_cost":
        enable_symmetry_breaking_atom_cost = True

    parent_search_data = mapsearch.PrimSearchData(
        prim=parent_xtal_prim,
        enable_symmetry_breaking_atom_cost=enable_symmetry_breaking_atom_cost,
    )

    # Create a StructureSearchData object for the child structure.
    child_search_data = mapsearch.StructureSearchData(
        lattice=child.lattice(),
        atom_coordinate_cart=child.atom_coordinate_cart(),
        atom_type=child.atom_type(),
        override_structure_factor_group=None,
    )

    # Create a MappingSearch object.
    # This will hold a queue of possible mappings,
    # sorted by cost, as we generate them.
    if atom_cost_method == "isotropic_disp_cost":
        atom_cost_f = mapsearch.IsotropicAtomCost()
    else:
        atom_cost_f = mapsearch.SymmetryBreakingAtomCost()

    search = mapsearch.MappingSearch(
        min_cost=min_cost,
        max_cost=max_cost,
        k_best=k_best,
        atom_cost_f=atom_cost_f,
        total_cost_f=mapsearch.WeightedTotalCost(
            lattice_cost_weight=lattice_cost_weight
        ),
        atom_to_site_cost_f=mapsearch.make_atom_to_site_cost,
        enable_remove_mean_displacement=enable_remove_mean_displacement,
        infinity=infinity,
        cost_tol=cost_tol,
    )

    constraints = mapsearch.QueueConstraints(
        min_queue_cost=min_queue_cost,
        max_queue_cost=max_queue_cost,
        max_queue_size=max_queue_size,
    )

    # Create superstructures of the prim as the child structures
    # that will be mapped back to the parent prim.
    # ScelEnum.by_volume guarantees supercells in canonical form
    scel_enum = casmenum.ScelEnum(
        prim=parent_prim,
    )
    for i, supercell in enumerate(scel_enum.by_volume(min=min_vol, max=max_vol)):
        if debug:
            print("\n##############\n")
            print(f"Supercell {i}:")
            print("Transformation matrix to supercell:")
            print(supercell.transformation_matrix_to_super)
            print("Superlattice (column_vector_matrix):")
            print(supercell.superlattice.column_vector_matrix())
            print()

        # for each child, make lattice mapping solutions
        lattice_mappings = mapmethods.map_lattices(
            lattice1=parent_xtal_prim.lattice(),
            lattice2=child_search_data.lattice(),
            transformation_matrix_to_super=supercell.transformation_matrix_to_super,
            lattice1_point_group=parent_search_data.prim_crystal_point_group(),
            lattice2_point_group=child_search_data.structure_crystal_point_group(),
            min_cost=lattice_mapping_min_cost,
            max_cost=lattice_mapping_max_cost,
            cost_method=lattice_cost_method,
            k_best=lattice_mapping_k_best,
            reorientation_range=lattice_mapping_reorientation_range,
            cost_tol=lattice_mapping_cost_tol,
        )

        for scored_lattice_mapping in lattice_mappings:
            lattice_mapping_data = mapsearch.LatticeMappingSearchData(
                prim_data=parent_search_data,
                structure_data=child_search_data,
                lattice_mapping=scored_lattice_mapping,
            )

            # for each lattice mapping, generate possible translations
            trial_translations = mapsearch.make_trial_translations(
                lattice_mapping_data=lattice_mapping_data,
            )

            # for each combination of lattice mapping and translation,
            # make and insert a mapping solution (MappingNode)
            for trial_translation in trial_translations:
                search.make_and_insert_mapping_node(
                    lattice_cost=scored_lattice_mapping.lattice_cost(),
                    lattice_mapping_data=lattice_mapping_data,
                    trial_translation_cart=trial_translation,
                    forced_on=forced_on,
                    forced_off=forced_off,
                )

    constraints.enforce(search)
    i_step = 0
    if debug:
        print(f"step {i_step}: queue: {search.size()}")

    while search.size():
        if debug:
            print(
                f"- atom_cost: {search.front().atom_cost()}, "
                f"lattice_cost: {search.front().lattice_cost()}"
            )
        search.partition()
        constraints.enforce(search)
        if debug:
            print(f"step {i_step}: queue: {search.size()}")
        i_step += 1

    return search.results()
