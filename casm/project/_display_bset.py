from typing import Optional, TextIO
import sys

import libcasm.configuration as casmconfig
from ._print_bset import PrettyPrintBasisOptions


def display_occ_site_functions(
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
    import latex2mathml.converter
    import IPython.display

    def display(s: str):
        IPython.display.display(IPython.display.HTML(latex2mathml.converter.convert(s)))

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
    s = R"\phi_{b,f}(s_l)"
    display(s)
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
            s = R"\begin{split}" + "\n"
            value = sublat_func.get("occ").get("value")
            first = True
            for i_function, function_values in enumerate(value):
                # print(f"  - \\phi_{{{b}, {i_function}}}: {function_values}", file=out)
                if not first:
                    s += R"\\" + "\n"
                s += f"\\phi_{{{b}, {i_function}}} &= {function_values}" + "\n"
                first = False
            s += "\n"
            s += R"\end{split}"
            IPython.display.display(
                IPython.display.HTML(latex2mathml.converter.convert(s))
            )


def display_functions(
    basis_dict: dict,
    prim: casmconfig.Prim,
    options: Optional[PrettyPrintBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    """Display cluster function formulas using IPython.display

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
    import latex2mathml.converter
    import IPython.display

    if out is None:
        out = sys.stdout
    if options is None:
        options = PrettyPrintBasisOptions()

    # prints nothing if no occupation site basis functions are found
    display_occ_site_functions(
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
        print(
            f"Orbit {orbit.get('linear_orbit_index')}: mult={orbit.get('mult')}",
            file=out,
        )
        # functions
        s = R"\begin{split}" + "\n"
        first = True
        functions = orbit.get("cluster_functions")
        for func in functions:
            if not first:
                s += R"\\" + "\n"
            linear_function_index = func.get("linear_function_index")
            key = R"\Phi_{" + str(linear_function_index) + "}"
            latex_formula = func.get(key)
            s += f"{key} = {latex_formula}"
            first = False
        s += "\n"
        s += R"\end{split}"
        IPython.display.display(IPython.display.HTML(latex2mathml.converter.convert(s)))
        print(file=out)
