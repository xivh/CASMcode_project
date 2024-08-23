from typing import Optional, TextIO
import sys

import libcasm.configuration as casmconfig


class PrettyPrintBasisOptions:
    """Options for pretty-printing a basis set"""

    def __init__(
        self,
        print_invariant_group: bool = True,
        linear_orbit_indices: Optional[set[int]] = None,
    ):
        self.print_invariant_group = print_invariant_group
        """bool: Print the invariant group of the cluster"""

        self.linear_orbit_indices = linear_orbit_indices
        """Optional[set[int]]: Linear cluster orbit indices to print. If None, all 
        orbits are printed."""


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
    print("- sites:", file=out)
    print("  - {[b, i, j, k]}", file=out)

    sites = cluster.get("sites")
    if len(sites) == 0:
        print("  - None", file=out)
    else:
        for site in sites:
            print(f"  - {site}", file=out)

    # site-to-site distances
    print(f"- site-to-site distances:", file=out)
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
        desc = cluster.get("invariant_group_descriptions")
        i = 0
        for fg, desc in zip(indices, desc):
            print(f"  - {i} ({fg}): {desc}", file=out)
            i += 1


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
    site_functions_dict: dict,
    prim: casmconfig.Prim,
    options: Optional[PrettyPrintBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    """Pretty print information about occupation site basis functions

    - Prints nothing if no occupation site basis functions found

    Parameters
    ----------
    site_functions_dict: dict
        A description of the site_functions, from the contents of a `basis.json`
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

    has_occ_site_functions = False
    for sublat_func in site_functions_dict:
        if "occ" in sublat_func:
            has_occ_site_functions = True
            break
    if not has_occ_site_functions:
        return

    print("Occupation site functions:", file=out)
    print("- \\phi_{i_sublattice, i_function}: {[value1, ...]}", file=out)
    occ_dof = prim.xtal_prim.occ_dof()
    for sublat_func in site_functions_dict:
        b = sublat_func.get("sublat")

        # sublat header, ex: - sublattice: 0, occ_dof: [Si, Ge]
        s = f"- sublattice: {b}, occ_dof: ["
        for name in occ_dof[b]:
            s += f"{name}, "
        s = s[:-2]
        s += "]"
        print(s, file=out)

        # each occ site basis function:
        if "occ" in sublat_func:
            value = sublat_func.get("occ").get("value")
            for i_function, function_values in enumerate(value):
                print(f"  - \\phi_{{{b}, {i_function}}}: {function_values}", file=out)


def pretty_print_functions(
    basis_dict: dict,
    prim: casmconfig.Prim,
    options: Optional[PrettyPrintBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    """Pretty print information about the functions of a basis set

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

    # prints nothing if no occupation site basis functions are found
    pretty_print_occ_site_functions(
        site_functions_dict=basis_dict.get("site_functions"),
        prim=prim,
        options=options,
        out=out,
    )
    print(file=out)

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
        print("- cluster functions:", file=out)
        print("  - \\Phi_{linear_function_index}: {latex_formula}", file=out)
        for func in functions:
            linear_function_index = func.get("linear_function_index")
            key = "\\Phi_{" + str(linear_function_index) + "}"
            latex_formula = func.get(key)
            print(f"  - {key} = {latex_formula}", file=out)
        print(file=out)
