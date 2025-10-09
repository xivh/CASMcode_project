import copy
import json
import pathlib
import time
from typing import Any, Optional, Union

import bokeh.document  # Document
import bokeh.models  # ColumnDataSource, Slider
import bokeh.plotting
import numpy as np
import scipy.spatial.transform

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal

from ._view import (
    make_cartesian_view_basis,
    make_lattice_cell_data,
    make_projection_from_dict,
)

default_component_params_path = (
    pathlib.Path(__file__).parent / "default_component_params.json"
)
with open(default_component_params_path, "r") as f:
    default_component_params = json.load(f)


def _format_plot(p):
    # p.xaxis.axis_label = x_label
    # p.yaxis.axis_label = y_label

    font_size_1 = "14pt"
    font_size_2 = "10pt"
    font_name = "roboto-mono, sans-serif, monospace"

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


Va_default_color = "#dcdcdc"
Va_default_line_width = 1.0


def make_generic_component_params(chemical_names: list[str]):
    if len(chemical_names) > 7:
        raise ValueError(
            "Error in make_generic_component_params: "
            "len(chemical_names) > 7; please provide custom `component_params`"
        )

    # Use bokeh color palette Set1:
    component_params = {}
    for i, chemical_name in enumerate(chemical_names):
        if chemical_name.lower() == "va":
            color = Va_default_color
            line_width = Va_default_line_width
            line_dash = "dotted"
        else:
            color = bokeh.palettes.Colorblind7[i % 7]
            line_width = 0.25
            line_dash = "solid"
        component_params[chemical_name] = dict(
            color=color,
            size=10,
            alpha=0.8,
            line_color="black",
            line_width=line_width,
            line_dash=line_dash,
        )
    return component_params


def make_component_params(
    chemical_names: list[str],
    preferred_component_params: Optional[dict] = None,
):
    component_params = {}

    _chemical_names = copy.deepcopy(chemical_names)
    _chemical_names.sort()

    if preferred_component_params is not None:
        # If a preferred set of component params is provided, use that.
        try:
            for i, chemical_name in enumerate(_chemical_names):
                component_params[chemical_name] = copy.deepcopy(
                    preferred_component_params[chemical_name]
                )
        # As a fallback, use bokeh Colorblind7 palette.
        except Exception:
            component_params = make_generic_component_params(
                chemical_names=_chemical_names
            )

    else:
        try:
            for i, chemical_name in enumerate(_chemical_names):
                if chemical_name.lower() == "va":
                    component_params[chemical_name] = default_component_params["Va"]
                else:
                    component_params[chemical_name] = default_component_params[
                        chemical_name
                    ]

        # As a fallback, use bokeh Colorblind7 palette.
        except Exception:
            component_params = make_generic_component_params(
                chemical_names=_chemical_names
            )

    return component_params


def make_prim_component_params(
    prim: Union[casmconfig.Prim, list[casmconfig.Prim]],
    preferred_component_params: Optional[dict] = None,
):
    """Make component parameters for one or more Prim

    Parameters
    ----------
    prim: Union[casmconfig.Prim, list[casmconfig.Prim]]
        The Prim or list of Prims to make component parameters for.
    preferred_component_params: dict[str, dict]
        The preferred component parameters to use for the components.

    Returns
    -------
    component_params: dict[str, dict]
        The component parameters for each chemical species.

    """
    if not isinstance(prim, list):
        prim = [prim]

    chemical_names = set()
    for p in prim:
        for occupant in p.xtal_prim.occupants().values():
            chemical_names.add(occupant.name())
    chemical_names = list(chemical_names)
    chemical_names.sort()

    return make_component_params(
        chemical_names=chemical_names,
        preferred_component_params=preferred_component_params,
    )


def adjust_color(color: str, factor: float = -0.3):
    """Make a color a bit darker or lighter.

    Parameters
    ----------
    color: str
        The color to adjust. Must be a valid matplotlib color.
    factor: float
        The factor to shift the RGB values by. Must be between -1 and 1.

    Returns
    -------
    adjusted_color: str
        The adjusted color as a hex string.

    """
    import matplotlib.colors

    rgb = np.array(matplotlib.colors.to_rgb(color))
    tol = 0.001
    for i in range(3):
        if factor < 0 - tol:
            rgb[i] = rgb[i] * (1.0 + factor)
        elif factor > 0 + tol:
            rgb[i] = rgb[i] + (1.0 - rgb[i]) * factor
    adjusted_rgb = np.clip(rgb, 0, 1)
    adjusted_color = matplotlib.colors.to_hex(adjusted_rgb)
    return adjusted_color


def make_highlight_params(
    component_params: dict,
    highlight_color: str = "cyan",
    highlight_width: float = 2.0,
):
    highlight_params = dict(component_params)

    for name, params in highlight_params.items():
        params["line_alpha"] = 1.0

    for name, params in component_params.items():

        new_params = dict(params)

        new_params["color"] = adjust_color(params["color"], factor=-0.3)
        new_params["line_color"] = highlight_color
        new_params["line_width"] = highlight_width
        new_params["line_alpha"] = 1.0
        highlight_params[name + "_sel"] = new_params
    return highlight_params


def update_highlight_params(
    component_params: dict,
    highlight_color: str,
    highlight_width: float = 2.0,
):
    for name, params in component_params.items():
        if name.endswith("_sel"):
            params["line_color"] = highlight_color
            params["line_width"] = highlight_width
            params["line_alpha"] = 1.0


class ViewAtomicStructureParams:
    def __init__(
        self,
        images_a_range: int = 1,
        images_b_range: int = 1,
        images_c_range: int = 1,
        images_m_range: int = 1,
        marker_size_scale: float = 1.0,
        marker_alpha_scale: float = 1.0,
        projection: Any = None,
        component_params: Optional[dict] = None,
    ):
        self.images_a_range = images_a_range
        self.images_b_range = images_b_range
        self.images_c_range = images_c_range
        self.images_m_range = images_m_range
        self.marker_size_scale = marker_size_scale
        self.marker_alpha_scale = marker_alpha_scale
        self.projection = projection
        if component_params is None:
            # Get first record in configuration set:
            record = next(iter(self.configuration_set))
            component_params = make_prim_component_params(
                prim=record.configuration.supercell.prim
            )
        self.component_params = component_params

    # to_dict:
    def to_dict(self):
        return {
            "images_a_range": self.images_a_range,
            "images_b_range": self.images_b_range,
            "images_c_range": self.images_c_range,
            "images_m_range": self.images_m_range,
            "marker_size_scale": self.marker_size_scale,
            "marker_alpha_scale": self.marker_alpha_scale,
            "projection": self.projection.to_dict(),
            "component_params": self.component_params,
        }

    # from_dict:
    @staticmethod
    def from_dict(data):
        return ViewAtomicStructureParams(
            images_a_range=data["images_a_range"],
            images_b_range=data["images_b_range"],
            images_c_range=data["images_c_range"],
            images_m_range=data["images_m_range"],
            marker_size_scale=data["marker_size_scale"],
            marker_alpha_scale=data["marker_alpha_scale"],
            projection=make_projection_from_dict(data["projection"]),
            component_params=data["component_params"],
        )


class ViewAtomicStructure:
    """View :class:`~libcasm.xtal.Structure` in a bokeh figure"""

    def __init__(
        self,
        doc: bokeh.document.Document,
        lattice_segment_params: dict,
        component_params: dict[str, dict],
        v1: Optional[np.ndarray] = None,
        v2: Optional[np.ndarray] = None,
        projection: Any = None,
        marker_size_scale: float = 1.0,
        marker_alpha_scale: float = 1.0,
        figure_params: Optional[dict] = None,
    ):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        doc : bokeh.document.Document
            The Bokeh document
        lattice_segment_params : dict
            A dict of keyword arguments to pass to :func:`bokeh.plotting.figure` when
            creating the lattice cell segments. Example:

            .. code-block:: python

                lattice_segment_params = dict(
                    color="green",
                    line_width=2,
                )

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
        projection: Any = None
            A projection object that defines how to project 3D coordinates to 2D.
            Default is None.
        marker_size_scale: float = 1.0
            A scale factor to apply to the marker sizes.
        marker_alpha_scale: float = 1.0
            A scale factor to apply to the marker alpha values.
        figure_params: dict = None
            A dict of keyword arguments to pass to :func:`bokeh.plotting.figure` when
            creating the figure. If None, default parameters are used.

        """
        self.system = None
        """libcasm.clexmonte.System: The Monte Carlo system."""

        self.doc = doc
        """bokeh.document.Document: The Bokeh document, used to add callbacks that
        update the figure."""

        self.lattice_segment_params = lattice_segment_params
        """dict: A dict of keyword arguments to pass to :func:`bokeh.plotting.figure` 
        when creating the lattice cell segments. Example:
        
        .. code-block:: python
        
            lattice_segment_params = dict(
                color="green",
                line_width=2,
            )
        
        """

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

        self.marker_size_scale = marker_size_scale
        """float: A scale factor to apply to the marker sizes."""

        self.marker_alpha_scale = marker_alpha_scale
        """float: A scale factor to apply to the marker alpha values."""

        self.v1 = v1
        """np.ndarray: A shape `(3,)` array giving the Cartesian vector that should lie
        along the horizontal axis."""

        self.v2 = v2
        """np.ndarray: A shape `(3,)` array giving the Cartesian vector that should lie
        along the vertical axis."""

        self.projection = projection
        """Any: A projection object that defines how to project 3D coordinates to 2D.
        Default uses :class:`~libcasm.project.plot.SinglePointProjection`."""

        if figure_params is None:
            figure_params = dict(
                width=600,
                height=400,
                match_aspect=True,
            )
        if "title" in figure_params:
            del figure_params["title"]

        self.figure_params = figure_params
        """dict: A dict of keyword arguments to pass to :func:`bokeh.plotting.figure` 
        when creating the figure. If None, default parameters are used."""

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

        self.figure_source = bokeh.models.ColumnDataSource(data=dict())
        """bokeh.models.ColumnDataSource: The Bokeh data source used to set the figure
        parameters, like the title."""

        self.structure = None
        """libcasm.xtal.Structure: The structure to view."""

        self.structure_name = None
        """str: The name of the structure to view."""

        self.plot = None
        """bokeh.plotting.figure: The Bokeh figure."""

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
        new_projection: Any = None,
        new_lattice_segment_params: Optional[dict] = None,
        new_component_params: Optional[dict] = None,
    ):
        self.structure = structure.copy()
        self.title = title

        if new_marker_size_scale is not None:
            self.marker_size_scale = new_marker_size_scale
        if new_marker_alpha_scale is not None:
            self.marker_alpha_scale = new_marker_alpha_scale
        if new_projection is not None:
            self.projection = new_projection
        if new_lattice_segment_params is not None:
            self.lattice_segment_params = new_lattice_segment_params
        if new_component_params is not None:
            self.component_params = new_component_params

        # make component_params_keys
        component_params_keys = None
        if self.component_params is not None:
            for _params in self.component_params.values():
                keys = sorted(list(_params.keys()))
                if component_params_keys is None:
                    component_params_keys = keys
                elif keys != component_params_keys:
                    raise ValueError(
                        "Error in ViewConfiguration2d: "
                        "component_params must have the same keys for all components"
                    )
        self.component_params_keys = component_params_keys
        """list[str]: The keys of the component_params dict, sorted alphabetically."""

        # Create initial data:
        data = dict()

        # Add Cartesian coordinates
        coordinate_cart = self.structure.atom_coordinate_cart()
        data["x"] = coordinate_cart[0, :]
        data["y"] = coordinate_cart[1, :]
        data["z"] = coordinate_cart[2, :]

        # Add projected coordinates
        coordinate_view = self.view_basis_inv @ coordinate_cart
        if self.projection is not None:
            self.projection.apply(coordinate_view)
        data["px"] = coordinate_view[0, :]
        data["py"] = coordinate_view[1, :]
        data["pz"] = coordinate_view[2, :]

        # Add component properties
        atom_type = self.structure.atom_type()
        for key in self.component_params_keys:
            if key == "radius_pm":
                data["radius"] = list()
                for name in atom_type:
                    data["radius"].append(
                        self.component_params[name][key]
                        * self.marker_size_scale
                        / 100.0
                        / 2.0
                    )
                data["radius"] = self.projection.projected_radius(
                    radius=data["radius"],
                    values=coordinate_view,
                )
            elif key == "alpha":
                data[key] = list()
                for name in atom_type:
                    alpha = self.component_params[name][key] * self.marker_alpha_scale
                    if alpha < 0.0:
                        alpha = 0.0
                    if alpha > 1.0:
                        alpha = 1.0
                    data[key].append(alpha)
            else:
                data[key] = list()
                for name in atom_type:
                    data[key].append(self.component_params[name][key])

        # Get indices of `data["pz"]` in sorted order (least to greatest):
        sorted_indices = np.argsort(data["pz"])

        # Sort all data entries by `data["pz"]`:
        for key in data.keys():
            data[key] = np.array(data[key])[sorted_indices].tolist()

        # Add lattice vectors
        lattice_cell_data = make_lattice_cell_data(
            lattice=self.structure.lattice(),
            view_basis=self.view_basis,
            projection=self.projection,
            center=False,
            shift=None,
            hex=False,
            dim=3,
            **self.lattice_segment_params,
        )

        if self.doc is None:
            self.source.data = data
            self.lattice_cell_source.data = lattice_cell_data
            self.figure_source.data = {
                "title": [self.title],
            }
        if self.doc is not None:

            def callback():
                self.source.data = data
                self.lattice_cell_source.data = lattice_cell_data
                self.figure_source.data = {
                    "title": [self.title],
                }

            # Set data source
            self.doc.add_next_tick_callback(callback)

            time.sleep(0.001)

    def make_plot(self):
        title = "(None)"
        if len(self.figure_source.data) != 0:
            title = self.figure_source.data["title"][0]
        p = bokeh.plotting.figure(title=title, **self.figure_params)

        if len(self.lattice_cell_source.data) != 0:
            p.segment(
                x0="px0",
                y0="py0",
                x1="px1",
                y1="py1",
                source=self.lattice_cell_source,
                line_color="line_color",
                line_width="line_width",
                line_dash="line_dash",
            )

        if len(self.source.data) != 0:
            scatter_kwargs = {x: x for x in self.component_params_keys}
            if "size" in scatter_kwargs:
                del scatter_kwargs["size"]
            if "radius_pm" in scatter_kwargs:
                del scatter_kwargs["radius_pm"]

            p.circle(
                "px",
                "py",
                "radius",
                source=self.source,
                **scatter_kwargs,
            )

        _format_plot(p)

        self.plot = p

        return p
