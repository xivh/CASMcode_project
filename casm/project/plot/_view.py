import math
from typing import Any, Optional

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


class CabinetProjection:
    """A cabinet perspective projection."""

    def __init__(self, scale: float = 0.2, angle: float = math.pi / 6.0):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        scale: float = 0.2
            A factor indicating fraction of "real" length displayed for vectors
            perpendicular to the viewing plane. A typical value is 0.2.
        angle: float = math.pi / 6.0
            The angle the vectors are displayed at. A typical value is pi/6.
        """

        self.scale = scale
        """float: A factor indicating fraction of "real" length displayed for vectors
        perpendicular to the viewing plane."""

        self.angle = angle
        """float: The angle the vectors are displayed at."""

        self.label = "Cabinet"
        """str: A label for the projection type."""

    def apply(self, values):
        """Apply the cabinet perspective projection to values.

        Parameters
        ----------
        values: np.array[np.float[3,n]]
            A shape ``(3, n)`` array of values to apply the cabinet perspective to
            where the columns are coordinate values in the view basis.
        """
        apply_cabinet((self.scale, self.angle), values)

    def projected_radius(self, radius: np.ndarray, values: np.ndarray) -> np.ndarray:
        """Get the projected radius due to cabinet projection.

        Parameters
        ----------
        radius: np.ndarray
            A shape `(n,)` array of radii to project.
        values: np.ndarray
            A shape `(3, n)` array of values in the view basis.

        Returns
        -------
        projected_radius: np.ndarray
            A shape `(n,)` array of projected radii.
        """
        return np.array(radius)

    def to_dict(self):
        """Serialize to a dictionary."""
        return {"type": "cabinet", "scale": self.scale, "angle": self.angle}

    @staticmethod
    def from_dict(data):
        """Deserialize from a dictionary."""
        if data["type"] != "cabinet":
            raise ValueError(
                "Error in CabinetProjection.from_dict: Invalid projection type"
            )
        return CabinetProjection(scale=data["scale"], angle=data["angle"])


class SinglePointProjection:
    """A single point perspective projection."""

    def __init__(self, viewer_distance: float = 100.0, plane_offset: float = 50.0):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        viewer_distance: float = 10.0
            The distance from the viewer to the projection plane, in terms of the
            3rd coordinate of the view basis.
        plane_offset: float = 10.0
            The position of the projection plane from the origin of the view basis,
            along the 3rd view basis axis.
        """

        self.viewer_distance = viewer_distance
        """float: The distance from the viewer to the projection plane, in terms of
        the 3rd coordinate of the view basis."""

        self.plane_offset = plane_offset
        """float: The position of the projection plane from the origin of the view 
        basis, along the 3rd view basis axis."""

        self.label = "Single point"
        """str: A label for the projection type."""

    def apply(self, values):
        """Apply the single point perspective projection to values.

        Parameters
        ----------
        values: np.array[np.float[3,n]]
            A shape ``(3, n)`` array of values to apply the single point perspective
            projection to, where the columns are coordinate values in the view basis.
        """
        # Apply perspective projection:
        # x' = x / (1 + (z_plane - z) / d_viewer)
        # y' = y / (1 + (z_plane - z) / d_viewer)

        d = self.viewer_distance

        for i in range(values.shape[1]):
            delta_z = self.plane_offset - values[2, i]
            values[0, i] /= 1.0 + delta_z / d
            values[1, i] /= 1.0 + delta_z / d

    # Get change in radius due to perspective (i.e. change in x + delta_x):
    def projected_radius(self, radius: np.ndarray, values: np.ndarray) -> np.ndarray:
        """Get the projected radius due to perspective.

        Parameters
        ----------
        radius: np.ndarray
            A shape `(n,)` array of radii to project.
        values: np.ndarray
            A shape `(3, n)` array of values in the view basis.

        Returns
        -------
        projected_radius: np.ndarray
            A shape `(n,)` array of projected radii.
        """
        d = self.viewer_distance
        projected_radius = np.array(radius)
        for i in range(values.shape[1]):
            delta_z = self.plane_offset - values[2, i]
            projected_radius[i] /= 1.0 + delta_z / d
        return projected_radius

    def to_dict(self):
        """Serialize to a dictionary."""
        return {
            "type": "single_point",
            "viewer_distance": self.viewer_distance,
            "plane_offset": self.plane_offset,
        }

    @staticmethod
    def from_dict(data):
        """Deserialize from a dictionary."""
        if data["type"] != "single_point":
            raise ValueError(
                "Error in SinglePointProjection.from_dict: Invalid projection type"
            )
        return SinglePointProjection(
            viewer_distance=data["viewer_distance"],
            plane_offset=data["plane_offset"],
        )


class IsometricProjection:
    """An isometric projection."""

    def __init__(self):
        """
        .. rubric:: Constructor
        """

        self.label = "Isometric"
        """str: A label for the projection type."""

    def apply(self, values):
        """Apply the isometric projection to values.

        Parameters
        ----------
        values: np.array[np.float[3,n]]
            A shape ``(3, n)`` array of values to apply the isometric projection to,
            where the columns are coordinate values in the view basis.
        """
        # Coordinates are already put into isometric view basis, so nothing to do
        pass

    def projected_radius(self, radius: np.ndarray, values: np.ndarray) -> np.ndarray:
        """Get the projected radius due to isometric projection.

        Parameters
        ----------
        radius: np.ndarray
            A shape `(n,)` array of radii to project.
        values: np.ndarray
            A shape `(3, n)` array of values in the view basis.

        Returns
        -------
        projected_radius: np.ndarray
            A shape `(n,)` array of projected radii.
        """
        return np.array(radius)

    def to_dict(self):
        """Serialize to a dictionary."""
        return {"type": "isometric"}

    @staticmethod
    def from_dict(data):
        """Deserialize from a dictionary."""
        if data["type"] != "isometric":
            raise ValueError(
                "Error in IsometricProjection.from_dict: Invalid projection type"
            )
        return IsometricProjection()


def make_projection_from_dict(data):
    """Deserialize a projection from a dictionary."""
    if data["type"] == "cabinet":
        return CabinetProjection.from_dict(data)
    elif data["type"] == "single_point":
        return SinglePointProjection.from_dict(data)
    elif data["type"] == "isometric":
        return IsometricProjection.from_dict(data)
    else:
        raise ValueError("Error in make_projection_from_dict: Invalid projection type")


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
    projection: Any = None,
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
    projection: Any = None
        A projection to apply to the view. If None, no projection is applied.
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
    if projection is not None:
        projection.apply(begin_values)
    end_values = view_basis_inv @ end_cart
    if projection is not None:
        projection.apply(end_values)

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
