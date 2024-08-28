import io

import latex2mathml.converter

import libcasm.configuration as casmconfig
from casm.project._print_bset import (
    pretty_print_functions,
    pretty_print_occ_site_functions,
)
from casm.project.json_io import read_required


def test_latex_to_html():
    ### Example usage: ###

    # from IPython.display import display, HTML
    # import latex2mathml.converter
    # s = R"""\begin{split}
    # \Phi_{2} &= \phi_{1} + \phi_{2} \\
    # \Phi_{3} + \Phi_{4} &= \phi_{3} + \phi_{4}
    # \end{split}
    # """
    # s_html = HTML(latex2mathml.converter.convert(s))
    # display(s_html)

    print("Inline")
    latex_input = R"\Phi_{2} = \phi_{1} + \phi_{2}"
    mathml_output = latex2mathml.converter.convert(latex_input)
    print(mathml_output)
    print()

    print("align")
    latex_input = R"""\begin{align}
\Phi_{2} &= \phi_{1} + \phi_{2} \\
\Phi_{3} &= \phi_{4} + \phi_{4}
\end{align}
"""
    mathml_output = latex2mathml.converter.convert(latex_input)
    print(mathml_output)
    print()

    assert False


def test_site_functions(shared_datadir):
    prim = casmconfig.Prim.from_dict(
        data=read_required(shared_datadir / "SiGe_prim.json"),
    )
    # basis_dict = read_required(shared_datadir / "SiGe_basis.json")
    variables = read_required(shared_datadir / "SiGe_variables.json")

    s = io.StringIO()
    pretty_print_occ_site_functions(
        variables=variables,
        prim=prim,
        out=s,
    )

    print(s.getvalue())
    assert (
        s.getvalue()
        == R"""Occupation site functions:
- \phi(s_n): [value1, ...], where:
  - n: neighborhood site index
  - s_n: occupation index on site n
- sublattice: 0, occ_dof: [Si, Ge]
  -    \phi_{I}(s_n) = [1.0, 1.0]
  -        \phi(s_n) = [-1.0, 1.0]
- sublattice: 1, occ_dof: [Si, Ge]
  -    \phi_{I}(s_n) = [1.0, 1.0]
  -        \phi(s_n) = [-1.0, 1.0]
"""
    )


def test_functions(shared_datadir):
    prim = casmconfig.Prim.from_dict(
        data=read_required(shared_datadir / "SiGe_prim.json"),
    )
    basis_dict = read_required(shared_datadir / "SiGe_basis.json")
    variables = read_required(shared_datadir / "SiGe_variables.json")

    pretty_print_functions(
        basis_dict=basis_dict,
        variables=variables,
        prim=prim,
    )

    assert False
