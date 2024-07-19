from casm.project._Project import Project


class SymCommand:
    """Methods to analyse and print symmetry information"""

    def __init__(self, proj: Project):
        self.proj = proj

    def print_lattice_point_group(
        self,
        brief: bool = True,
        coord: str = "frac",
    ):
        """Print the lattice point group"""
        return None

    def print_factor_group(
        self,
        brief: bool = True,
        coord: str = "frac",
    ):
        """Print the prim factor group"""
        return None

    def print_crystal_point_group(
        self,
        brief: bool = True,
        coord: str = "frac",
    ):
        """Print the crystal point group"""
        return None

    def dof_space_analysis(
        self,
    ):
        print("dof_space_analysis")
        return None

    def config_space_analysis(
        self,
    ):
        print("config_space_analysis")
        return None
