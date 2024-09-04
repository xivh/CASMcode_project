import math

import numpy as np

import libcasm.mapping.info as mapinfo
import libcasm.mapping.methods as mapmethods
import libcasm.xtal as xtal
import libcasm.xtal.prims as xtal_prims
from casm.project.structure_import import map_structure


def as_int(a: float):
    """Round floating point arrays that are approximately integer to integer arrays"""
    b = np.rint(a)
    if not np.allclose(a, b):
        raise Exception("Error converting to integer array: not approximately integer")
    return np.array(b, dtype=int)


def check_mapping(
    prim: xtal.Prim,
    structure: xtal.Structure,
    structure_mapping: mapinfo.ScoredStructureMapping,
):
    """Check that a structure mapping does map between a structure and a superstructure
    of a prim
    """
    # print("structure:")
    # print("lattice_column_vector_matrix:\n",
    #       structure.lattice().column_vector_matrix())
    # print("atom_coordinate_frac:\n", structure.atom_coordinate_frac().transpose())
    # print("atom_type:", structure.atom_type())
    mapped_structure = mapmethods.make_mapped_structure(structure_mapping, structure)
    mapped_structure_L = mapped_structure.lattice().column_vector_matrix()
    mapped_structure_atom_type = mapped_structure.atom_type()
    mapped_structure_atom_coordinate_frac = mapped_structure.atom_coordinate_frac()
    mapped_structure_atom_coordinate_cart = (
        mapped_structure_L @ mapped_structure_atom_coordinate_frac
    )

    # print("mapped_structure:")
    # print("lattice_column_vector_matrix:\n",
    #       mapped_structure.lattice().column_vector_matrix())
    # print("atom_coordinate_frac:\n",
    #       mapped_structure.atom_coordinate_frac().transpose())
    # print("atom_type:", mapped_structure_atom_type)

    # lattice mapping relation:
    # Q * U * L1 * T * N = L2
    lmap = structure_mapping.lattice_mapping()
    L1 = prim.lattice().column_vector_matrix()
    L2 = structure.lattice().column_vector_matrix()
    F = lmap.deformation_gradient()
    Q = lmap.isometry()
    U = lmap.right_stretch()
    T = as_int(lmap.transformation_matrix_to_super())
    N = as_int(lmap.reorientation())
    # print("F:\n", F)
    # print("Q:\n", Q)
    # print("U:\n", U)
    # print("T:\n", T)
    # print("N:\n", N)
    # print("L1 @ T @ N:\n", L1 @ T @ N)
    # print("U @ L1 @ T @ N:\n", U @ L1 @ T @ N)
    assert np.allclose(Q @ U @ L1 @ T @ N, L2)
    assert np.allclose(
        U @ L1 @ T @ N, mapped_structure.lattice().column_vector_matrix()
    )

    # atom mapping relation:
    # F ( r1(i) + disp(i) ) = r2(perm[i]) + trans
    # print("Check atom mapping:")
    prim_occ_dof = prim.occ_dof()
    prim_structure = xtal.Structure(
        lattice=prim.lattice(),
        atom_coordinate_frac=prim.coordinate_frac(),
        atom_type=[x[0] for x in prim_occ_dof],
    )

    ideal_superstructure = xtal.make_superstructure(T @ N, prim_structure)
    amap = structure_mapping.atom_mapping()
    r1 = ideal_superstructure.atom_coordinate_cart()
    r2 = structure.atom_coordinate_cart()
    disp = amap.displacement()
    perm = amap.permutation()
    trans = amap.translation()
    # print("disp:\n", disp.transpose())
    # print("perm:", perm)
    # print("trans:", trans)
    for i in range(r1.shape[1]):
        b = i % len(prim_occ_dof)
        assert mapped_structure_atom_type[i] in prim_occ_dof[b]
        if perm[i] >= r2.shape[1]:
            # implied vacancy
            assert mapped_structure_atom_type[i] == "Va"
        else:
            # check unmapped structure vs mapping with Q
            x1 = F @ (r1[:, i] + disp[:, i])
            x2 = r2[:, perm[i]] + trans
            d = xtal.min_periodic_displacement(structure.lattice(), x1, x2)
            assert math.isclose(np.linalg.norm(d), 0.0, abs_tol=1e-10)

            # check unmapped structure vs mapping without Q
            x1 = U @ (r1[:, i] + disp[:, i])
            x2 = mapped_structure_atom_coordinate_cart[:, i]
            d = xtal.min_periodic_displacement(structure.lattice(), x1, x2)
            assert math.isclose(np.linalg.norm(d), 0.0, abs_tol=1e-10)

    # atom mapping cost:
    # isotropic_atom_cost = make_isotropic_atom_cost(L1, lmap, disp)
    # print("isotropic_atom_cost:", isotropic_atom_cost)


def test_map_structure_0():
    """Map to vol 1 structure - cubic"""
    prim = xtal_prims.cubic(a=1.0, occ_dof=["A"])

    structure = xtal.Structure(
        lattice=prim.lattice(),
        atom_coordinate_frac=prim.coordinate_frac(),
        atom_type=["A"],
    )

    structure_mappings = map_structure(
        prim, structure, max_vol=1, max_cost=0.0, min_cost=0.0
    )
    assert len(structure_mappings) == 1

    smap = structure_mappings[0]
    assert math.isclose(smap.total_cost(), 0.0)
    check_mapping(prim, structure, smap)


def test_map_structure_1():
    """Map vol 2 structure - cubic"""
    prim = xtal_prims.cubic(a=1.0, occ_dof=["A"])

    unit_structure = xtal.Structure(
        lattice=prim.lattice(),
        atom_coordinate_frac=prim.coordinate_frac(),
        atom_type=["A"],
    )

    T = np.array(
        [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 2],
        ],
        dtype=int,
    )
    structure = xtal.make_superstructure(T, unit_structure)

    structure_mappings = map_structure(
        prim, structure, max_vol=2, max_cost=0.0, min_cost=0.0
    )
    assert len(structure_mappings) == 2

    for smap in structure_mappings:
        assert math.isclose(smap.total_cost(), 0.0)
        check_mapping(prim, structure, smap)


def test_map_structure_2():
    """Map vol 2 ordered structure - cubic"""
    prim = xtal_prims.cubic(a=1.0, occ_dof=["A"])

    unit_structure = xtal.Structure(
        lattice=prim.lattice(),
        atom_coordinate_frac=prim.coordinate_frac(),
        atom_type=["A"],
    )

    T = np.array(
        [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 2],
        ],
        dtype=int,
    )
    structure = xtal.make_superstructure(T, unit_structure)

    structure_mappings = map_structure(
        prim, structure, max_vol=2, max_cost=0.0, min_cost=0.0
    )
    assert len(structure_mappings) == 2

    for smap in structure_mappings:
        assert math.isclose(smap.total_cost(), 0.0)
        check_mapping(prim, structure, smap)


def test_map_structure_3():
    """Map vol 2 ordered structure to 2 site prim"""

    prim_lattice = xtal.Lattice(
        np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 2.0],
            ]
        ).transpose()
    )
    coordinate_frac = np.array(
        [
            [0.0, 0.25, 0.25],
            [0.0, 0.25, 0.75],
        ]
    ).transpose()
    occ_dof = [
        ["A"],
        ["B"],
    ]
    prim = xtal.Prim(
        lattice=prim_lattice, coordinate_frac=coordinate_frac, occ_dof=occ_dof
    )

    structure = xtal.Structure(
        lattice=prim.lattice(),
        atom_coordinate_frac=prim.coordinate_frac(),
        atom_type=["A", "B"],
    )

    structure_mappings = map_structure(
        prim, structure, max_vol=1, max_cost=0.0, min_cost=0.0
    )
    assert len(structure_mappings) == 1

    for smap in structure_mappings:
        assert math.isclose(smap.total_cost(), 0.0)
        check_mapping(prim, structure, smap)


def test_map_structures_4():
    """Map to Ezz && Eyz"""
    prim = xtal_prims.cubic(a=1.0, occ_dof=["A"])

    structure_lattice = xtal.Lattice(
        np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.1],
                [0.0, 0.0, 1.1],
            ]
        ).transpose()
    )
    structure = xtal.Structure(
        lattice=structure_lattice,
        atom_coordinate_frac=prim.coordinate_frac(),
        atom_type=["A"],
    )

    structure_mappings = map_structure(
        prim,
        structure,
        max_vol=1,
        max_cost=0.1,
        min_cost=0.0,
    )
    assert len(structure_mappings) == 1
    structure_mapping = structure_mappings[0]
    U = structure_mapping.lattice_mapping().right_stretch()
    assert np.allclose(
        U,
        np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.00362465, 0.05232166],
                [0.0, 0.05232166, 1.09875495],
            ]
        ),
    )

    for smap in structure_mappings:
        check_mapping(prim, structure, smap)


def test_map_structures_5():
    """Map to BCC: 1 implicit vacancy"""
    prim = xtal_prims.BCC(r=1.0, occ_dof=["A", "B", "Va"])
    prim_occ_dof = prim.occ_dof()
    L1 = prim.lattice().column_vector_matrix()

    # from scipy.spatial.transform import Rotation
    # Qi = Rotation.from_euler("z", 30, degrees=True).as_matrix()
    Qi = np.array([[0.8660254, -0.5, 0.0], [0.5, 0.8660254, 0.0], [0.0, 0.0, 1.0]])
    Ui = np.array([[1.01, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    Fi = Qi @ Ui

    T = np.eye(3, dtype=int) * 2
    prim_structure = xtal.Structure(
        lattice=prim.lattice(),
        atom_coordinate_frac=prim.coordinate_frac(),
        atom_type=[x[0] for x in prim_occ_dof],
    )
    ideal_superstructure = xtal.make_superstructure(T, prim_structure)

    structure_lattice = xtal.Lattice(Fi @ L1 @ T)
    disp_frac = np.array(
        [
            [0.01, -0.01, 0.01],
            [0.00, 0.01, -0.01],
            [0.01, 0.00, -0.01],
            [-0.01, 0.01, 0.0],
            [-0.01, 0.00, 0.01],
            [0.0, 0.00, -0.01],
            [0.01, 0.00, 0.0],
        ]
    ).transpose()
    atom_coordinate_frac = (
        ideal_superstructure.atom_coordinate_frac()[:, 1:] + disp_frac
    )
    structure = xtal.Structure(
        lattice=structure_lattice,
        atom_coordinate_frac=atom_coordinate_frac,
        atom_type=["A"] * 7,
    )

    structure_mappings = map_structure(
        prim,
        structure,
        max_vol=8,
        min_vol=8,
        max_cost=1e20,
        min_cost=0.0,
    )

    assert len(structure_mappings) == 1
    for smap in structure_mappings:
        check_mapping(prim, structure, smap)
