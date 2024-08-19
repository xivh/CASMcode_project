from casm.project._Project import Project


class ImportCommand:
    """Methods to import calculated structures as configurations with properties"""

    def __init__(self, proj: Project):
        self.proj = proj

    # TODO:
    #  - search for structure mappings
    #  - create mapped configurations with properties
    #  - select between possible mappings
    #  - import into a master list
