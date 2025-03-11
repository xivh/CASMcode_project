import time
from typing import Optional

import bokeh.document  # Document
import bokeh.models  # ColumnDataSource, Slider
import bokeh.plotting
import numpy as np
import scipy.spatial.transform

import libcasm.xtal as xtal

from ._view import (
    apply_cabinet,
    make_cartesian_view_basis,
    make_lattice_cell_data,
)


def _format_plot(p):
    # p.xaxis.axis_label = x_label
    # p.yaxis.axis_label = y_label

    font_size_1 = "14pt"
    font_size_2 = "10pt"
    font_name = "monospace"

    p.title.text_font = font_name
    p.title.text_font_size = font_size_1

    p.xaxis.axis_label_text_font = font_name
    p.xaxis.axis_label_text_font_size = font_size_1
    p.xaxis.major_label_text_font = font_name
    p.xaxis.major_label_text_font_size = font_size_2

    p.yaxis.axis_label_text_font = font_name
    p.yaxis.axis_label_text_font_size = font_size_1
    p.yaxis.major_label_text_font = font_name
    p.yaxis.major_label_text_font_size = font_size_2


class ViewAtomicStructure:
    """View :class:`~libcasm.xtal.Structure` in a bokeh figure"""

    def __init__(
        self,
        doc: bokeh.document.Document,
        component_params: dict[str, dict],
        v1: Optional[np.ndarray] = None,
        v2: Optional[np.ndarray] = None,
        cabinet: Optional[tuple[float, float]] = None,
        marker_size_scale: float = 1.0,
        marker_alpha_scale: float = 1.0,
    ):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        doc : bokeh.document.Document
            The Bokeh document
        component_params : dict[str, dict]
            A dict of component name to scatter plot keyword arguments. Every dict
            must have the same keys.

            Example:

            .. code-block:: python

                component_params = {
                    "A": dict(
                        color="red",
                        size=10,
                    ),
                    "B": dict(
                        color="blue",
                        size=20,
                    ),
                    "Va": dict(
                        color="gray",
                        size=20,
                    ),
                }

        v1: np.ndarray = [1.0, 0.0, 0.0]
            A shape `(3,)` array giving the Cartesian vector that should lie along
            the horizontal axis.
        v2: np.ndarray = [0.0, 0.0, 1.0]
            A shape `(3,)` array giving the Cartesian vector that should lie along
            the vertical axis.
        cabinet: Optional[tuple[float, float]] = None
            A tuple, :math:`(f, \theta)`, where :math:`f` is a factor indicating
            fraction of "real" length displayed for vectors perpendicular to the
            viewing plane, and :math:`\theta` is the angle the vectors are displayed
            at. A typical value is ``(0.2, math.pi/6.0)``.
        marker_size_scale: float = 1.0
            A scale factor to apply to the marker sizes.
        marker_alpha_scale: float = 1.0
            A scale factor to apply to the marker alpha values.

        """
        self.system = None
        """libcasm.clexmonte.System: The Monte Carlo system."""

        self.doc = doc
        """bokeh.document.Document: The Bokeh document, used to add callbacks that
        update the figure."""

        self.component_params = component_params
        """dict[str, dict]: A dict of component name to scatter plot keyword arguments.

        Every dict must have the same keys. For example:

        .. code-block:: python

            component_params = {
                "A": dict(
                    color="red",
                    size=10,
                ),
                "B": dict(
                    color="blue",
                    size=20,
                ),
                "Va": dict(
                    color="gray",
                    size=20,
                ),
            }

        """

        # make component_params_keys
        component_params_keys = None
        for _params in component_params.values():
            keys = sorted(list(_params.keys()))
            if component_params_keys is None:
                component_params_keys = keys
            elif keys != component_params_keys:
                raise ValueError(
                    "Error in ViewConfiguration2d: component_params must have the same "
                    "keys for all components"
                )
        self.component_params_keys = component_params_keys
        """list[str]: The keys of the component_params dict, sorted alphabetically."""

        self.marker_size_scale = marker_size_scale
        """float: A scale factor to apply to the marker sizes."""

        self.v1 = v1
        """np.ndarray: A shape `(3,)` array giving the Cartesian vector that should lie
        along the horizontal axis."""

        self.v2 = v2
        """np.ndarray: A shape `(3,)` array giving the Cartesian vector that should lie
        along the vertical axis."""

        self.cabinet = cabinet
        """Optional[tuple[float, float]]: Optional "cabinet" perspective parameters.
        
        A tuple, :math:`(f, \theta)`, where :math:`f` is a factor indicating fraction
        of "real" length displayed for vectors perpendicular to the viewing plane, and
        :math:`\theta` is the angle the vectors are displayed at. A typical value is
        ``(0.2, math.pi/6.0)``.
        """

        self.view_basis = make_cartesian_view_basis(v1=v1, v2=v2)
        """np.ndarray: The inverse of the view basis, :math:`B`, a shape `(3, 3)` array 
        giving the basis vectors that should be used to view the Cartesian coordinates 
        such that `v1` lies along the horizontal axis and `v2` lies along the vertical 
        axis.

        .. math::

            x^{cart} = B x^{view}

        where :math:`x^{view}` are the projected coordinates, as columns, and
        :math:`x^{cart}` are the Cartesian, as columns.
        """

        self.view_basis_inv = np.linalg.pinv(self.view_basis)
        """np.ndarray: The inverse of the view basis, :math:`B^{-1}`.

        .. math::

            x^{view} = B^{-1} x^{cart}

        where :math:`x^{view}` are the projected coordinates, as columns, and 
        :math:`x^{cart}` are the Cartesian, as columns. 
        """

        self.source = bokeh.models.ColumnDataSource(data=dict())
        """bokeh.models.ColumnDataSource: The Bokeh data source used to create the
        figure."""

        self.lattice_cell_source = bokeh.models.ColumnDataSource(data=dict())
        """bokeh.models.ColumnDataSource: The Bokeh data source used to create the
        lattice cell lines."""

        self.structure = None
        """libcasm.xtal.Structure: The structure to view."""

        self.structure_name = None
        """str: The name of the structure to view."""

    def update_view_basis(
        self,
        v1: Optional[np.ndarray] = None,
        v2: Optional[np.ndarray] = None,
    ):
        """Update the view basis.

        Parameters
        ----------
        v1: np.ndarray = None
            A shape `(3,)` array giving the new Cartesian vector that should lie along
            the horizontal axis. If None, the current `v1` is used.
        v2: np.ndarray = None
            A shape `(3,)` array giving the new Cartesian vector that should lie along
            the vertical axis. If None, the current `v2` is used.

        """
        if v1 is not None:
            self.v1 = v1
        if v2 is not None:
            self.v2 = v2

        self.view_basis = make_cartesian_view_basis(v1=self.v1, v2=self.v2)
        self.view_basis_inv = np.linalg.pinv(self.view_basis)

        if self.structure is not None:
            self.set_structure(
                structure=self.structure,
                title=self.title,
            )

    def rotate_view_basis(
        self,
        v_axis: np.ndarray,
        angle: float,
    ):
        """Rotate the view basis vectors by an angle about an axis.

        Parameters
        ----------
        v_axis: np.ndarray
            The axis to rotate about. Will be normalized.
        angle: float
            The angle to rotate by in degrees.

        """
        v_axis = np.array(v_axis)
        v_axis_normalized = v_axis / np.linalg.norm(v_axis)

        # Convert angle from degrees to radians
        angle_rad = np.deg2rad(angle)

        # Get the rotation matrix
        rotation = scipy.spatial.transform.Rotation.from_rotvec(
            v_axis_normalized * angle_rad
        )
        rotation_matrix = rotation.as_matrix()

        # Rotate the view basis
        self.view_basis = self.view_basis @ rotation_matrix
        self.view_basis_inv = np.linalg.pinv(self.view_basis)

        if self.structure is not None:
            self.set_structure(
                structure=self.structure,
                title=self.title,
            )

    def set_structure(
        self,
        structure: xtal.Structure,
        title: str,
        new_marker_size_scale: Optional[float] = None,
        new_marker_alpha_scale: Optional[float] = None,
        new_cabinet: Optional[tuple[float, float]] = None,
    ):
        self.structure = structure.copy()
        self.title = title

        if new_marker_size_scale is not None:
            self.marker_size_scale = new_marker_size_scale
        if new_marker_alpha_scale is not None:
            self.marker_alpha_scale = new_marker_alpha_scale
        if new_cabinet is not None:
            self.cabinet = new_cabinet

        # Create initial data:
        data = dict()

        # Add Cartesian coordinates
        coordinate_cart = self.structure.atom_coordinate_cart()
        data["x"] = coordinate_cart[0, :]
        data["y"] = coordinate_cart[1, :]
        data["z"] = coordinate_cart[2, :]

        # Add projected coordinates
        coordinate_view = self.view_basis_inv @ coordinate_cart
        apply_cabinet(self.cabinet, coordinate_view)
        data["px"] = coordinate_view[0, :]
        data["py"] = coordinate_view[1, :]
        data["pz"] = coordinate_view[2, :]

        # Add component properties
        atom_type = self.structure.atom_type()
        for key in self.component_params_keys:
            data[key] = list()
            if key == "size":
                for name in atom_type:
                    data[key].append(
                        self.component_params[name][key] * self.marker_size_scale
                    )
            elif key == "alpha":
                for name in atom_type:
                    alpha = self.component_params[name][key] * self.marker_alpha_scale
                    if alpha < 0.0:
                        alpha = 0.0
                    if alpha > 1.0:
                        alpha = 1.0
                    data[key].append(alpha)
            else:
                for name in atom_type:
                    data[key].append(self.component_params[name][key])

        # Add lattice vectors
        lattice_cell_data = make_lattice_cell_data(
            lattice=self.structure.lattice(),
            view_basis=self.view_basis,
            cabinet=self.cabinet,
            center=False,
            shift=None,
            hex=False,
            dim=3,
        )

        if self.doc is None:
            self.source.data = data
            self.lattice_cell_source.data = lattice_cell_data
        if self.doc is not None:

            def callback():
                self.source.data = data
                self.lattice_cell_source.data = lattice_cell_data

            # Set data source
            self.doc.add_next_tick_callback(callback)

            time.sleep(0.001)

    def make_plot(self):
        figure_params = dict(
            title=self.title,
            width=600,
            height=400,
            match_aspect=True,
        )
        p = bokeh.plotting.figure(**figure_params)

        scatter_kwargs = {x: x for x in self.component_params_keys}

        p.segment(
            x0="px0",
            y0="py0",
            x1="px1",
            y1="py1",
            source=self.lattice_cell_source,
            color="green",
            line_width=2,
        )

        p.scatter(
            "px",
            "py",
            source=self.source,
            **scatter_kwargs,
        )

        _format_plot(p)

        return p
