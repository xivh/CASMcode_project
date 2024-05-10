import numpy as np
from typing import Iterable, Optional, Union
import libcasm.configuration as casmconfig
from casm.project._Project import Project
from casm.project.json_io import (
    read_required,
    safe_dump,
)


class ImportCommand:
    """Methods to import calculated structures as configurations with properties"""

    def __init__(self, proj: Project):
        self.proj = proj

    # TODO:
    #  - search for structure mappings
    #  - create mapped configurations with properties
    #  - select between possible mappings
    #  - import into a master list
