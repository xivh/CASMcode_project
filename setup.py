__version__ = "2.0a1"

# Available at setup time due to pyproject.toml
from setuptools import setup

setup(
    name="casm-project",
    version=__version__,
    packages=[
        "casm",
        "casm.project",
        "casm.project.bset",
        "casm.project.calc",
        "casm.project.enum",
        "casm.project.fit",
        "casm.project.plot",
        "casm.project.structure_import",
        "casm.project.sym",
        "casm.project.system",
        "casm.vis",
    ],
    install_requires=[],
)
