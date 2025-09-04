import pathlib
import shutil

# Path to the examples directory:
examples_dir = pathlib.Path(__file__).resolve().parent

# Clean up generated files
dir = examples_dir / "enum_occ_by_supercell_Ising"
shutil.rmtree(dir / ".ipynb_checkpoints", ignore_errors=True)
shutil.rmtree(dir / "Ising_occ", ignore_errors=True)

dir = examples_dir / "enum_occ_by_supercell_SiGe"
shutil.rmtree(dir / ".ipynb_checkpoints", ignore_errors=True)
shutil.rmtree(dir / "SiGe_occ", ignore_errors=True)
