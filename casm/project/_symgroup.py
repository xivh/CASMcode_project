import libcasm.configuration as casmconfig
import libcasm.sym_info as sym_info
from libcasm.configuration.io.spglib import asdict as spg_asdict
from libcasm.configuration.io.spglib import (
    get_magnetic_spacegroup_type_from_symmetry,
    get_spacegroup_type_from_symmetry,
)


def symgroup_to_dict_with_group_classification(
    prim: casmconfig.Prim,
    symgroup: sym_info.SymGroup,
) -> dict:
    """Use spglib to add group classification to SymGroup data

    Notes
    -----

    - This version only uses the symmetry operations found by CASM.

    Parameters
    ----------
    prim: libcasm.configuration.Prim
        The prim
    symgroup: libcasm.sym_info.SymGroup
        The SymGroup

    Returns
    -------
    data: dict
        The ``SymGroup.to_dict()`` output with the following added to the
        ``data["group_classification"]`` attribute:

        - ``"spacegroup_type"``: Space group type information from spglib, based on the
          symmetry operations found by CASM.

        - ``"magnetic_spacegroup_type"``: Space group type information
          from spglib, based on the symmetry operations found by CASM. Only
          added if there are magnetic spin DoF.

    """
    lattice = prim.xtal_prim.lattice()
    data = symgroup.to_dict(lattice=lattice)

    is_magnetic = False
    if (
        prim.discrete_atomic_magspin_key is not None
        or prim.continuous_magspin_key is not None
    ):
        is_magnetic = True
    # prim.discrete_molecular_magspin_key (not implemented)
    for name, occupant in prim.xtal_prim.occupants().items():
        for key, value in occupant.properties().items():
            if "magspin" in key:
                is_magnetic = True

    nonmagnetic_elements = [
        op for op in symgroup.elements if op.time_reversal() is False
    ]
    spacegroup_type = spg_asdict(
        get_spacegroup_type_from_symmetry(nonmagnetic_elements, lattice)
    )
    grpcls = data["group_classification"]
    grpcls["spacegroup_type"] = spacegroup_type

    if is_magnetic:
        mag_spacegroup_type = spg_asdict(
            get_magnetic_spacegroup_type_from_symmetry(symgroup.elements, lattice)
        )
        grpcls["magnetic_spacegroup_type"] = mag_spacegroup_type

    return data
