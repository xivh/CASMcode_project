import copy
import sys
from typing import Optional, TextIO

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal
from casm.bset.misc import (
    irrational_to_tex_string,
)
from libcasm.sym_info import (
    SymGroup,
)


class PrettyPrintBasisOptions:
    """Options for pretty-printing a basis set"""

    def __init__(
        self,
        linear_function_indices: Optional[set[int]] = None,
        linear_orbit_indices: Optional[set[int]] = None,
        function_type: str = "orbit",
        basis_site_index: Optional[int] = None,
        print_invariant_group: bool = True,
        invariant_group_coordinate_mode: str = "cart",
        site_coordinate_mode: str = "integral",
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        linear_function_indices: Optional[set[int]] = None
            Linear basis function indices to display. If None, all functions are
            displayed.
        linear_orbit_indices: Optional[set[int]] = None
            Linear cluster orbit indices to print. If None, all orbits are printed.
        function_type: str = "orbit"
            Type of functions to print. Options are:

            - "prototype": Print the equivalent cluster basis
              functions that are associated with the prototype cluster only. Variables
              are indexed using neighbor list indices.
            - "prototype_with_cluster_indices": Print the equivalent cluster basis
              functions that are associated with the prototype cluster only. Variables
              are indexed using indices into sites in the prototype cluster.
            - "orbit": Print equivalent cluster basis functions on all clusters in an
              orbit, for the contribution associated with the origin unit cell.
              Variables are indexed using neighbor list indices.
            - "site": Print equivalent cluster basis functions for all cluster
              functions that include a particular site. Variables are indexed using
              neighbor list indices. The site is specified by `basis_site_index`.
            - "occ_delta_site": Print equivalent cluster basis functions for all cluster
              functions that include a particular site. Variables are indexed using
              neighbor list indices. The site is specified by `basis_site_index`.
              Functions give the change in basis function values when the occupation
              of the site is changed.

        basis_site_index: Optional[int] = None
            If `function_type` is "site" or "occ_delta_site", the site-centric
            functions are displayed for the `basis_site_index`-th basis site in the
            origin unit cell.

        print_invariant_group: bool = True
            Print the invariant group of the cluster
        invariant_group_coordinate_mode: str = "cart"
            Coordinate mode for printing invariant group elements. Options are:

            - 'cart': Use Cartesian coordinates
            - 'frac': Use fractional coordinates, with respect to the Prim lattice
              vectors

        site_coordinate_mode: str = "integral"
            Coordinate mode for printing cluster sites. Options are:

            - 'integral': Use :class:`~libcasm.xtal.IntegralSiteCoordinate`
              ([b, i, j, k])
            - 'cart': Use Cartesian coordinates
            - 'frac': Use fractional coordinates, with respect to the Prim lattice
              vectors

        """
        self.linear_function_indices = linear_function_indices
        """Optional[set[int]]: Linear function indices to display. If None, all 
        functions are displayed."""

        self.linear_orbit_indices = linear_orbit_indices
        """Optional[set[int]]: Linear cluster orbit indices to print. 

        If None, all orbits are printed.
        """

        self.function_type = function_type
        """str: Type of functions to print. 

        Options are:

        - "prototype": Print the equivalent cluster basis
          functions that are associated with the prototype cluster only. Variables
          are indexed using neighbor list indices.
        - "prototype_with_cluster_indices": Print the equivalent cluster basis
          functions that are associated with the prototype cluster only. Variables
          are indexed using indices into sites in the prototype cluster.
        - "orbit": Print equivalent cluster basis functions on all clusters in an
          orbit, for the contribution associated with the origin unit cell.
          Variables are indexed using neighbor list indices.
        - "site": Print equivalent cluster basis functions for all cluster
          functions that include a particular site. Variables are indexed using
          neighbor list indices. The site is specified by `basis_site_index`.
        - "occ_delta_site": Print equivalent cluster basis functions for all cluster
          functions that include a particular site. Variables are indexed using
          neighbor list indices. The site is specified by `basis_site_index`.
          Functions give the change in basis function values when the occupation
          of the site is changed.

        """

        self.basis_site_index = basis_site_index
        """Optional[int]: If `function_type` is "site", the site-centric functions are
        displayed for the `basis_site_index`-th basis site in the origin unit cell."""

        self.print_invariant_group = print_invariant_group
        """bool: Print the invariant group of the cluster"""

        self.invariant_group_coordinate_mode = invariant_group_coordinate_mode
        """str: Coordinate mode for printing invariant group elements.
        
        Options are:
        
            - 'cart': Use Cartesian coordinates
            - 'frac': Use fractional coordinates, with respect to the Prim lattice
              vectors
        """

        self.site_coordinate_mode = site_coordinate_mode
        """str: Coordinate mode for printing cluster sites
        
        Mode for printing coordinates. Options are:

        - 'integral': Use :class:`~libcasm.xtal.IntegralSiteCoordinate`
          ([b, i, j, k])
        - 'cart': Use Cartesian coordinates
        - 'frac': Use fractional coordinates, with respect to the Prim lattice
          vectors
        """


def print_site(
    site: xtal.IntegralSiteCoordinate,
    prim: casmconfig.Prim,
    options: PrettyPrintBasisOptions,
    out: TextIO,
):
    if options.site_coordinate_mode == "integral":
        print(f"  - {site}", file=out)
    elif options.site_coordinate_mode == "cart":
        print(f"  - {site.coordinate_cart(prim.xtal_prim)}", file=out)
    elif options.site_coordinate_mode == "frac":
        print(f"  - {site.coordinate_frac(prim.xtal_prim)}", file=out)
    else:
        raise ValueError(f"Invalid coordinate mode: {options.site_coordinate_mode}")


def pretty_print_cluster(
    cluster_dict: dict,
    prim: casmconfig.Prim,  # TODO: select coordinate mode
    options: Optional[PrettyPrintBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    if out is None:
        out = sys.stdout
    if options is None:
        options = PrettyPrintBasisOptions()

    cluster = cluster_dict

    # sites
    if options.site_coordinate_mode == "integral":
        print("- sites: (integral coordinates)", file=out)
        print("  - {[b, i, j, k]}", file=out)
    elif options.site_coordinate_mode == "cart":
        print("- sites: (Cartesian coordinates)", file=out)
        print("  - {x, y, z}", file=out)
    elif options.site_coordinate_mode == "frac":
        print("- sites: (fractional coordinates)", file=out)
        print("  - {a, b, c}", file=out)
    else:
        raise ValueError(f"Invalid coordinate mode: {options.site_coordinate_mode}")

    sites = cluster.get("sites")
    if len(sites) == 0:
        print("  - None", file=out)
    else:
        for site in sites:
            print_site(
                site=xtal.IntegralSiteCoordinate.from_list(site),
                prim=prim,
                options=options,
                out=out,
            )

    # site-to-site distances
    print("- site-to-site distances:", file=out)
    distances = cluster.get("distances")
    if len(distances) == 0:
        print("  - None", file=out)
    else:
        for dist in cluster.get("distances"):
            print(f"  - {dist:.6f}", file=out)

    # symgroup
    if options.print_invariant_group:
        print("- cluster invariant group:", file=out)
        print(
            "  - {cluster_group_index} ({prim_factor_group_index}): {sym_op_desc}",
            file=out,
        )
        indices = cluster.get("invariant_group")

        cluster_group = SymGroup.from_elements(
            elements=[prim.factor_group.elements[i] for i in indices],
            lattice=prim.xtal_prim.lattice(),
            sort=False,
        )

        # desc = cluster.get("invariant_group_descriptions")
        i_cg = 0
        for op in cluster_group.elements:
            info = xtal.SymInfo(
                op=op,
                lattice=prim.xtal_prim.lattice(),
            )
            i_fg = cluster_group.head_group_index[i_cg]
            if options.invariant_group_coordinate_mode == "cart":
                desc = info.brief_cart()
            elif options.invariant_group_coordinate_mode == "frac":
                desc = info.brief_frac()
            else:
                raise ValueError(
                    f"Invalid coordinate mode: "
                    f"{options.invariant_group_coordinate_mode}"
                )
            print(f"  - {i_cg} ({i_fg}): {desc}", file=out)
            i_cg += 1


def pretty_print_orbit(
    orbit_dict: dict,
    prim: casmconfig.Prim,
    options: Optional[PrettyPrintBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    if out is None:
        out = sys.stdout
    if options is None:
        options = PrettyPrintBasisOptions()

    orbit = orbit_dict
    print(f"Orbit {orbit.get('linear_orbit_index')}:", file=out)
    print(f"- linear_orbit_index: {orbit.get('linear_orbit_index')}", file=out)
    print(f"- multiplicity: {orbit.get('mult')}", file=out)
    pretty_print_cluster(
        cluster_dict=orbit.get("prototype"),
        prim=prim,
        options=options,
        out=out,
    )


def pretty_print_orbits(
    basis_dict: dict,
    prim: casmconfig.Prim,
    options: Optional[PrettyPrintBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    """Pretty print information about the orbits of a basis set

    Parameters
    ----------
    basis_dict: dict
        A description of a cluster expansion basis set, the contents of a `basis.json`
        file.
    prim: casmconfig.Prim
        The prim.
    options: Optional[PrettyPrintBasisOptions] = None
        Options for pretty-printing the basis set. If None, default options are used.
    out: Optional[stream] = None
        Output stream. Defaults to `sys.stdout`.

    """
    if out is None:
        out = sys.stdout
    if options is None:
        options = PrettyPrintBasisOptions()

    for orbit in basis_dict.get("orbits"):
        linear_orbit_index = orbit.get("linear_orbit_index")
        if (
            options.linear_orbit_indices is not None
            and linear_orbit_index not in options.linear_orbit_indices
        ):
            continue
        pretty_print_orbit(orbit_dict=orbit, prim=prim, options=options, out=out)
        print(file=out)


def pretty_print_occ_site_functions(
    variables: dict,
    prim: casmconfig.Prim,
    options: Optional[PrettyPrintBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    """Pretty print information about occupation site basis functions

    - Prints nothing if no occupation site basis functions found

    Parameters
    ----------
    variables: dict
        The contents of a `variables.json` file.
    prim: casmconfig.Prim
        The prim.
    options: Optional[PrettyPrintBasisOptions] = None
        Options for pretty-printing the basis set. If None, default options are used.
    out: Optional[stream] = None
        Output stream. Defaults to `sys.stdout`.

    """
    if out is None:
        out = sys.stdout
    if options is None:
        options = PrettyPrintBasisOptions()

    occ_site_functions = variables.get("occ_site_functions")
    if len(occ_site_functions) == 0:
        return

    info = variables.get("occ_site_functions_info")
    occ_var_name = info.get("occ_var_name")
    occ_var_indices = info.get("occ_var_indices")

    if options.function_type in ["prototype_with_cluster_indices"]:
        site_labels = "  - n: cluster site index"
    else:
        site_labels = "  - n: neighborhood site index"

    print("Occupation site functions:", file=out)
    print(f"- {occ_var_name}" + "(\\vec{r}_{n}): [value1, ...]", end="", file=out)
    if len(occ_var_indices) > 0:
        print(", where:", file=out)
        for name, desc in occ_var_indices:
            print(f"  - {name}: {desc}", file=out)
        print(site_labels, file=out)
        print("  - \\vec{r}_{n}: site position", file=out)
    else:
        print(", where:", file=out)
        print(site_labels, file=out)
        print("  - \\vec{r}_{n}: site position", file=out)
    occ_dof = prim.xtal_prim.occ_dof()
    for sublat_func in occ_site_functions:
        b = sublat_func.get("sublattice_index")
        m_constant = sublat_func.get("constant_function_index")

        # sublat header, ex: - sublattice: 0, occ_dof: [Si, Ge]
        s = f"- sublattice: {b}, occ_dof: ["
        for name in occ_dof[b]:
            s += f"{name}, "
        s = s[:-2]
        s += "]"
        print(s, file=out)

        # each occ site basis function:
        value = sublat_func.get("value")
        for m, function_values in enumerate(value):
            _values = "["
            first = True
            for v in function_values:
                if not first:
                    _values += ", "
                first = False
                limit = 24
                max_pow = 2
                v_tex = irrational_to_tex_string(
                    v, limit=limit, max_pow=max_pow, abs_tol=1e-5
                )
                _values += v_tex
            _values += "]"

            if m == m_constant:
                # varname = "\\phi_{I}(\\vec{r}_{n})"
                # print(f"  - {varname:>16} = {_values}", file=out)
                pass
            else:
                varname = occ_var_name.format(b=b, m=m) + "(\\vec{r}_{n})"
                print(
                    f"  - {varname:>16} = {_values}",
                    file=out,
                )


def pretty_print_functions_by_orbit(
    basis_dict: dict,
    variables: dict,
    prim: casmconfig.Prim,
    options: Optional[PrettyPrintBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    """Pretty print information about the functions of a basis set

    Parameters
    ----------
    basis_dict: dict
        The contents of a `basis.json` file.
    variables: dict
        The contents of a `variables.json` file.
    prim: casmconfig.Prim
        The prim.
    options: Optional[PrettyPrintBasisOptions] = None
        Options for pretty-printing the basis set. If None, default options are used.
    out: Optional[stream] = None
        Output stream. Defaults to `sys.stdout`.

    """
    if out is None:
        out = sys.stdout
    if options is None:
        options = PrettyPrintBasisOptions()

    # prints nothing if no occupation site basis functions are found
    pretty_print_occ_site_functions(
        variables=variables,
        prim=prim,
        options=options,
        out=out,
    )
    print(file=out)

    orbit_bfuncs = variables.get("orbit_bfuncs")
    orbit_bfuncs_by_index = {}
    for x in orbit_bfuncs:
        orbit_bfuncs_by_index[x.get("linear_function_index")] = copy.deepcopy(x)
    site_bfuncs = variables.get("site_bfuncs")
    site_bfuncs_by_index = {}
    for x in site_bfuncs:
        site_bfuncs_by_index[x.get("linear_function_index")] = copy.deepcopy(x)

    is_site_functions = False
    if options.function_type in ["site", "occ_delta_site"]:
        is_site_functions = True
        if options.basis_site_index is None:
            raise ValueError(
                "If function type is 'site' or 'occ_delta_site', "
                "the basis_site_index must be specified"
            )

    for orbit in basis_dict.get("orbits"):
        linear_orbit_index = orbit.get("linear_orbit_index")

        if options.linear_orbit_indices is not None:
            if linear_orbit_index not in options.linear_orbit_indices:
                continue

        pretty_print_orbit(orbit_dict=orbit, prim=prim, options=options, out=out)

        # functions
        functions = orbit.get("cluster_functions")
        if options.function_type in ["orbit"]:
            print("- cluster functions: (orbit formulas)", file=out)
        elif options.function_type in ["prototype", "prototype_with_cluster_indices"]:
            print("- cluster functions: (prototype cluster formulas)", file=out)
        elif options.function_type in ["site", "occ_delta_site"]:
            print("- cluster functions: (site-centric formulas)", file=out)
        else:
            raise ValueError(f"Invalid function type: {options.function_type}")
        print("  - \\Phi_{linear_function_index}: {latex_formula}", file=out)
        for func in functions:
            linear_function_index = func.get("linear_function_index")

            key = "\\Phi_{" + str(linear_function_index) + "}"

            latex_formula = "(none)"
            if not is_site_functions:
                if linear_function_index in orbit_bfuncs_by_index:
                    orbit_bfunc = orbit_bfuncs_by_index.get(linear_function_index)
                    if options.function_type == "prototype_with_cluster_indices":
                        formula = orbit_bfunc.get("latex_prototype")
                    elif options.function_type == "prototype":
                        formula = orbit_bfunc.get(
                            "latex_prototype_with_neighbor_indices"
                        )

                    elif options.function_type == "orbit":
                        formula = orbit_bfunc.get("latex_orbit")
                    else:
                        raise ValueError(
                            f"Invalid function type: {options.function_type}"
                        )
                    latex_formula = formula.replace("\n", "\n  ")
            else:
                if linear_function_index in site_bfuncs_by_index:
                    site_bfunc = site_bfuncs_by_index.get(linear_function_index)
                    if len(site_bfunc.get("at")) > 0:
                        site_data = site_bfunc.get("at")[options.basis_site_index]
                        if options.function_type == "site":
                            formula = site_data.get("latex")
                        elif options.function_type == "occ_delta_site":
                            formula = site_data.get("occ_delta_latex")
                        else:
                            raise ValueError(
                                f"Invalid function type: {options.function_type}"
                            )
                        if formula is not None:
                            latex_formula = formula.replace("\n", "\n  ")
            print(f"  - {key} = {latex_formula}", file=out)
        print(file=out)
