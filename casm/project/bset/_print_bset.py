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
        print_invariant_group: bool = True,
        invariant_group_coordinate_mode: str = "cart",
        linear_orbit_indices: Optional[set[int]] = None,
        print_prototypes: bool = False,
        site_coordinate_mode: str = "integral",
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        print_invariant_group: bool = True
            Print the invariant group of the cluster
        invariant_group_coordinate_mode: str = "cart"
            Coordinate mode for printing invariant group elements. Options are:

            - 'cart': Use Cartesian coordinates
            - 'frac': Use fractional coordinates, with respect to the Prim lattice
              vectors

        linear_orbit_indices: Optional[set[int]] = None
            Linear cluster orbit indices to print. If None, all orbits are printed.
        print_prototypes: bool = False
            Print the function prototypes if True, orbit basis functions otherwise
        site_coordinate_mode: str = "integral"
            Coordinate mode for printing cluster sites. Options are:

            - 'integral': Use :class:`~libcasm.xtal.IntegralSiteCoordinate`
              ([b, i, j, k])
            - 'cart': Use Cartesian coordinates
            - 'frac': Use fractional coordinates, with respect to the Prim lattice
              vectors

        """
        self.print_invariant_group = print_invariant_group
        """bool: Print the invariant group of the cluster"""

        self.invariant_group_coordinate_mode = invariant_group_coordinate_mode
        """str: Coordinate mode for printing invariant group elements.
        
        Options are:
        
            - 'cart': Use Cartesian coordinates
            - 'frac': Use fractional coordinates, with respect to the Prim lattice
              vectors
        """

        self.linear_orbit_indices = linear_orbit_indices
        """Optional[set[int]]: Linear cluster orbit indices to print. 
        
        If None, all orbits are printed.
        """

        self.print_prototypes = print_prototypes
        """bool: Print the function prototypes if True, orbit basis functions 
        otherwise"""

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

    if options.print_prototypes:
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


def pretty_print_functions(
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

    for orbit in basis_dict.get("orbits"):
        linear_orbit_index = orbit.get("linear_orbit_index")
        if (
            options.linear_orbit_indices is not None
            and linear_orbit_index not in options.linear_orbit_indices
        ):
            continue

        pretty_print_orbit(orbit_dict=orbit, prim=prim, options=options, out=out)

        # functions
        functions = orbit.get("cluster_functions")
        if options.print_prototypes is False:
            print("- cluster functions: (orbit formulas)", file=out)
        else:
            print("- cluster functions: (prototype cluster formulas)", file=out)
        print("  - \\Phi_{linear_function_index}: {latex_formula}", file=out)
        for func in functions:
            linear_function_index = func.get("linear_function_index")
            key = "\\Phi_{" + str(linear_function_index) + "}"

            latex_formula = "(skipped)"
            if linear_function_index in orbit_bfuncs_by_index:
                orbit_bfunc = orbit_bfuncs_by_index.get(linear_function_index)
                if options.print_prototypes:
                    latex_formula = orbit_bfunc.get("latex_prototype").replace(
                        "\n", "\n  "
                    )
                else:
                    latex_formula = orbit_bfunc.get("latex_orbit").replace("\n", "\n  ")
            print(f"  - {key} = {latex_formula}", file=out)
        print(file=out)
