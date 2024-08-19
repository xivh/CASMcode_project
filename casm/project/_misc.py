import sys
from typing import Optional, TextIO

from tabulate import tabulate


def print_table(
    data: list[dict],
    columns: list[str],
    headers: list[str],
    out: Optional[TextIO] = None,
):
    """Print table from data in a list of dict

    Parameters
    ----------
    data: list[dict]
        Data to print
    columns: list[str]
        Keys of data to print, in order
    headers: list[str]
        Header strings
    out: Optional[stream] = None
        Output stream. Defaults to `sys.stdout`.
    """
    tabulate_in = []
    if out is None:
        out = sys.stdout
    for record in data:
        tabulate_in.append([record[col] for col in columns])
    out.write(tabulate(tabulate_in, headers=headers))
    out.write("\n")
