import math
from typing import Optional

import numpy as np

import libcasm.xtal as xtal


def begin_frac_2d():
    return np.array(
        [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
    ).transpose()


def end_frac_2d():
    return np.array(
        [[1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
    ).transpose()


def begin_frac():
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ]
    ).transpose()


def end_frac():
    return np.array(
        [
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
        ]
    ).transpose()


def hex_begin_frac():
    return np.array(
        [
            [0.0, 0.0, 0.0],  # center vertical
            [1.0, 0.0, 0.0],  # bottom hex
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],  # vertical-bottom
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 1.0],  # top hex
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
            [-1.0, 0.0, 1.0],
            [-1.0, -1.0, 1.0],
            [0.0, -1.0, 1.0],
        ]
    ).transpose()


def hex_end_frac():
    return np.array(
        [
            [0.0, 0.0, 1.0],  # center vertical
            [1.0, 1.0, 0.0],  # bottom hex
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 1.0],  # vertical-top
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
            [-1.0, 0.0, 1.0],
            [-1.0, -1.0, 1.0],
            [0.0, -1.0, 1.0],
            [1.0, 1.0, 1.0],  # top hex
            [0.0, 1.0, 1.0],
            [-1.0, 0.0, 1.0],
            [-1.0, -1.0, 1.0],
            [0.0, -1.0, 1.0],
            [1.0, 0.0, 1.0],
        ]
    ).transpose()


def hex_begin_frac_2d():
    return np.array(
        [
            [1.0, 0.0, 0.0],  # bottom hex
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
        ]
    ).transpose()


def hex_end_frac_2d():
    return np.array(
        [
            [1.0, 1.0, 0.0],  # bottom hex
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
    ).transpose()


def corners_frac():
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
        ]
    ).transpose()


def corners_frac_2d():
    return np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
    ).transpose()


def hex_corners_frac():
    return np.array(
        [
            [1.0, 1.0, 0.0],  # bottom hex
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],  # top hex
            [0.0, 1.0, 1.0],
            [-1.0, 0.0, 1.0],
            [-1.0, -1.0, 1.0],
            [0.0, -1.0, 1.0],
            [1.0, 0.0, 1.0],
        ]
    ).transpose()


def hex_corners_frac_2d():
    return np.array(
        [
            [1.0, 1.0, 0.0],  # bottom hex
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
    ).transpose()


def make_cartesian_view_basis(
    v1: Optional[np.ndarray] = None,
    v2: Optional[np.ndarray] = None,
):
    """Make a basis to view Cartesian coordinates such that v1 lies along the
    horizontal axis and v2 lies along the vertical axis.

    Parameters
    ----------
    v1: np.ndarray = [1.0, 0.0, 0.0]
        A shape `(3,)` array giving the Cartesian vector that should lie along
        the horizontal axis.
    v2: np.ndarray = [0.0, 0.0, 1.0]
        A shape `(3,)` array giving the Cartesian vector that should lie along
        the vertical axis.

    Returns
    -------
    basis: np.ndarray
        A shape `(3, 3)` array giving the basis vectors that should be used to
        view the Cartesian coordinates such that `v1` lies along the horizontal
        axis and `v2` lies along the vertical axis. The columns of the array are
        the basis vectors.

    """
    if v1 is None:
        v1 = np.array([1.0, 0.0, 0.0])
    else:
        v1 = np.array(v1)

    if v2 is None:
        v2 = np.array([0.0, 0.0, 1.0])
    else:
        v2 = np.array(v2)
    assert v1.shape[0] == 3
    assert v2.shape[0] == 3

    b1 = v1 / np.linalg.norm(v1)
    b2 = v2 - (v2 @ b1) * b1
    b2 = b2 / np.linalg.norm(b2)
    b3 = np.cross(b1, b2)

    return np.array([b1, b2, b3]).transpose()


def apply_cabinet(cabinet, values):
    """Apply 'cabinet' perspective to values. This is similar to how most people draw
    3d shapes (like a kitchen cabinet) by hand.

    Parameters
    ----------
    cabinet: tuple[float, float]
        A tuple, :math:`(f, \theta)`, where :math:`f` is a factor indicating fraction
        of "real" length displayed for vectors perpendicular to the viewing plane, and
        :math:`\theta` is the angle the vectors are displayed at. A typical value is
        ``(0.2, math.pi/6.0)``.
    values: np.array[np.float[3,n]]
        A shape ``(3, n)`` array of values to apply the cabinet perspective to, where
        the columns are coordinate values in the view basis.
    """
    if cabinet is not None:
        for i in range(values.shape[1]):
            values[0, i] += -cabinet[0] * values[2, i] * math.cos(cabinet[1])
            values[1, i] += -cabinet[0] * values[2, i] * math.sin(cabinet[1])


def make_lattice_cell_data(
    lattice: xtal.Lattice,
    view_basis: np.array,
    cabinet: Optional[tuple[float, float]] = None,
    center: bool = False,
    shift: Optional[np.array] = None,
    hex: bool = False,
    dim: int = 3,
):
    """Plot the lattice cell.

    Parameters
    ----------
    lattice: xtal.Lattice
        The lattice to plot.
    view_basis: np.array
        The view basis to use for plotting.
    cabinet: Optional[tuple[float, float]] = None
        Optional "cabinet" perspective parameters. A tuple, :math:`(f, \theta)`,
        where :math:`f` is a factor indicating fraction of "real" length displayed
        for vectors perpendicular to the viewing plane, and :math:`\theta` is the
        angle the vectors are displayed at. A typical value is ``(0.2, math.pi/6.0)``.
    center: bool = False
        If True, draw lattice so that cell body center is located
        at the origin.
    shift: Optional[np.array] = None
        If provided, lattice vectors begin at the Cartesian coordinates `shift`.
        The argument `center` takes precedence over `shift`.
    hex: bool = False
        Draw using standard hexagonal cell
    dim: int = 3
        Use dim==3 to draw 3d lattice cells, and dim==2 to draw 2d lattice
        cells.
    """
    view_basis_inv = np.linalg.pinv(view_basis)

    L = lattice.column_vector_matrix()
    L_inv = np.linalg.pinv(L)

    shift_frac = np.array([0.0, 0.0, 0.0])
    if center:
        shift_frac = np.array([-0.5, -0.5, -0.5])
        if hex is True:
            shift_frac = np.array([0.0, 0.0, -0.5])
    elif shift is not None:
        shift_frac = L_inv @ shift

    _begin_frac = None
    if hex is True:
        if dim == 3:
            _begin_frac = hex_begin_frac()
        elif dim == 2:
            _begin_frac = hex_begin_frac_2d()
    else:
        if dim == 3:
            _begin_frac = begin_frac()
        elif dim == 2:
            _begin_frac = begin_frac_2d()

    for i in range(_begin_frac.shape[1]):
        _begin_frac[:, i] = _begin_frac[:, i] + shift_frac

    _end_frac = None
    if hex is True:
        if dim == 3:
            _end_frac = hex_end_frac()
        elif dim == 2:
            _end_frac = hex_end_frac_2d()
    else:
        if dim == 3:
            _end_frac = end_frac()
        elif dim == 2:
            _end_frac = end_frac_2d()

    for i in range(_end_frac.shape[1]):
        _end_frac[:, i] = _end_frac[:, i] + shift_frac

    begin_cart = L @ _begin_frac
    end_cart = L @ _end_frac

    begin_values = view_basis_inv @ begin_cart
    apply_cabinet(cabinet, begin_values)
    end_values = view_basis_inv @ end_cart
    apply_cabinet(cabinet, end_values)

    # fig.segment(
    #     x0=begin_values[0, :],
    #     y0=begin_values[1, :],
    #     x1=end_values[0, :],
    #     y1=end_values[1, :],
    #     color="green",
    #     line_width=2,
    # )

    return {
        "px0": begin_values[0, :],
        "py0": begin_values[1, :],
        "px1": end_values[0, :],
        "py1": end_values[1, :],
    }
