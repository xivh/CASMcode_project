import numpy as np

import casm.project
import libcasm.xtal as xtal


def test_make_symmetrized_lattice_1():
    L = np.array(
        [
            [0.0, 0.7071067811865475, 0.7071067811865475],  # a
            [0.7071067811865475, 0.0, 0.7071067811865475],  # b
            [0.7071067811865475, 0.7071067811865475 + 0.0001, 0.0],  # c
        ]
    ).transpose()

    lattice = xtal.Lattice(column_vector_matrix=L, tol=1e-5)

    pg_1 = xtal.make_point_group(lattice)
    assert len(pg_1) == 4

    symmetrized_lattice = casm.project.make_symmetrized_lattice(
        lattice=lattice,
        tol=1e-3,
    )

    pg_2 = xtal.make_point_group(symmetrized_lattice)
    # print("L:\n", symmetrized_lattice.column_vector_matrix())
    assert len(pg_2) == 48
    assert symmetrized_lattice.tol() == 1e-5
