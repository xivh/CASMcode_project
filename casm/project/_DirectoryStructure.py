import pathlib
from typing import Optional, Union

from ._ClexDescription import ClexDescription


class DirectoryStructure:
    """Standard CASM project directory structure

    This class helps constructs the standard paths specified in the CASM
    `Project directory structure reference <https://prisms-center.github.io/CASMcode_docs/formats/project_directory_structure/>`_.

    """

    def __init__(self, path: Union[str, pathlib.Path]):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        path: Union[str, pathlib.Path]
            Path to CASM project directory.

        """
        self.path = pathlib.Path(path)
        """str: Path to CASM project."""

        if self.path is None:
            raise Exception(
                "Error in casm.project.DirectoryStructure: "
                f"No CASM project found containing {path}"
            )
        self.__casm_dir = ".casm"
        self.__casmdb_dir = "jsonDB"
        self.__enum_dir = "enumerations"
        self.__bset_dir = "basis_sets"
        self.__calc_dir = "training_data"
        self.__set_dir = "settings"
        self.__sym_dir = "symmetry"
        self.__clex_dir = "cluster_expansions"
        self.__system_dir = "systems"

    # ** Query filesystem **

    def all_enum(self):
        """Check filesystem directory structure and return list of all enumeration names"""
        return self.__all_settings("enum", self.path / self.__enum_dir)

    def all_bset(self):
        """Check filesystem directory structure and return list of all basis set names"""
        return self.__all_settings("bset", self.path / self.__bset_dir)

    def all_calctype(self):
        """Check filesystem directory structure and return list of all calctype names"""
        return self.__all_settings(
            "calctype", self.path / self.__calc_dir / self.__set_dir
        )

    def all_ref(self, calctype: str):
        """Check filesystem directory structure and return list of all ref names for a given calctype"""
        return self.__all_settings("ref", self.calc_settings_dir(calctype))

    def all_clex_name(self):
        """Check filesystem directory structure and return list of all cluster expansion names"""
        return self.__all_settings("clex", self.path / self.__clex_dir)

    def all_eci(self, property: str, calctype: str, ref: str, bset: str):
        """Check filesystem directory structure and return list of all eci names"""
        return self.__all_settings(
            "eci",
            self.path
            / self.__clex_dir
            / self.__clex_name(property)
            / self.__calctype(calctype)
            / self.__ref(ref)
            / self.__bset(bset),
        )

    def all_systems(self):
        return self.__all_settings("system", self.__system_dir)

    # ** File and Directory paths **

    # -- Project directory --------

    def root_dir(self):
        """Return casm project directory path"""
        return self.path

    def prim(self):
        """Return prim.json path"""
        return self.casm_dir() / "prim.json"

    # -- Hidden .casm directory --------

    def casm_dir(self):
        """Return hidden .casm dir path"""
        return self.path / self.__casm_dir

    def casmdb_dir(self):
        """Return .casm/jsonDB path"""
        return self.casm_dir() / self.__casmdb_dir

    def project_settings(self):
        """Return project_settings.json path"""
        return self.casm_dir() / "project_settings.json"

    def scel_list(self, scelname: str):
        """Return master scel_list.json path"""
        return self.casmdb_dir() / "scel_list.json"

    def config_list(self, name: Optional[str] = None):
        """Return configuration set or list file path

        Parameters
        ----------
        name: Optional[str] = None
            Optional name for configuration list or set. Default (None) is
            the master configuration set.

        """
        if name is None:
            filename = "config_list.json"
        else:
            filename = f"config_list.{name}.json"
        return self.casm_dbdir() / filename

    def config_props(
        self,
        calctype: str,
        name: Optional[str] = None,
    ):
        """Return configuration properties file path for given calculation type"""
        if name is None:
            filename = "config_props.json"
        else:
            filename = f"config_props.{name}.json"
        return self.casm_dbdir() / self.__calctype(calctype) / filename

    def event_list(self):
        """Return master occ_event_list.json file path"""
        return self.casm_dbdir() / "event_list.json"

    def path_list(self):
        """Return master path_list.json file path"""
        return self.casm_dbdir() / "path_list.json"

    def path_props(self, calctype, name: Optional[str] = None):
        """Return path_props.json file path for given calculation type"""
        if name is None:
            filename = "path_props.json"
        else:
            filename = f"path_props.{name}.json"
        return self.casm_dbdir() / self.__calctype(calctype) / filename

    def master_selection(self, otype):
        """Return location of MASTER selection file

        Parameters
        ----------
        otype: str
            One of "config", "scel", "event", or "path"
        """
        querydir = self.casm_dir() / "query"
        if otype == "config":
            return querydir / "Configuration" / "master_selection"
        elif otype == "scel":
            return querydir / "Supercell" / "master_selection"
        elif otype == "event":
            return querydir / "Event" / "master_selection"
        elif otype == "path":
            return querydir / "Path" / "master_selection"
        else:
            raise Exception("Unsupported type: " + str(otype))

    # -- Symmetry --------

    def symmetry_dir(self):
        """Return symmetry directory path"""
        return self.path / self.__sym_dir

    def lattice_point_group(self):
        """Return lattice_point_group.json path"""
        return self.symmetry_dir() / "lattice_point_group.json"

    def factor_group(self):
        """Return factor_group.json path"""
        return self.symmetry_dir() / "factor_group.json"

    def crystal_point_group(self):
        """Return crystal_point_group.json path"""
        return self.symmetry_dir() / "crystal_point_group.json"

    # -- Enumerations --------
    def enum_dir(
        self,
        enum: str,
    ):
        """Return path to directory contain enumeration info"""
        return self.path / self.__enum_dir / self.__enum(enum=enum)

    # -- Basis sets --------

    def _get_bset(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        if bset is None:
            if clex is None:
                raise Exception("One of clex, bset is required")
            bset = clex.bset
        return bset

    def bset_dir(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return path to directory contain basis set info"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.path / self.__bset_dir / self.__bset(bset=bset)

    def bspecs(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return basis function specs (bspecs.json) file path"""
        return self.bset_dir(clex=clex, bset=bset) / "bspecs.json"

    def clust(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to the clust.json file"""
        return self.bset_dir(clex=clex, bset=bset) / "clust.json"

    def basis(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to the basis.json file"""
        return self.bset_dir(clex=clex, bset=bset) / "basis.json"

    def clexulator_dir(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to directory containing global clexulator"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.bset_dir(clex)

    def clexulator_src(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to global clexulator source file"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.cc")

    def clexulator_o(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to global clexulator.o file"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.o")

    def clexulator_so(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to global clexulator so file"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.so")

    # -- Calculations and reference --------

    def supercell_dir(self, scelname: str, calc_subdir: str = ""):
        """Return supercell directory path (scelname has format SCELV_A_B_C_D_E_F)"""
        return self.path / self.__calc_dir / calc_subdir / scelname

    def configuration_dir(self, configname: str, calc_subdir: str = ""):
        """Return configuration directory path (configname has format SCELV_A_B_C_D_E_F/I)"""
        return self.path / self.__calc_dir / calc_subdir / configname

    def POS(self, configname: str, calc_subdir: str = ""):
        """Return path to POS file"""
        return self.configuration_dir(configname, calc_subdir) / "POS"

    def config_json(self, configname: str, calc_subdir: str = ""):
        """Return path to structure.json file"""
        return self.configuration_dir(configname, calc_subdir) / "structure.json"

    def structure_json(self, configname: str, calc_subdir: str = ""):
        """Return path to structure.json file"""
        return self.configuration_dir(configname, calc_subdir) / "structure.json"

    def calctype_dir(
        self, configname: str, clex: ClexDescription, calc_subdir: str = ""
    ):
        R"""Return calctype directory path (e.g. training_data/$(calc_subdir)/SCEL...../0/calctype.default"""
        return self.configuration_dir(configname, calc_subdir) / self.__calctype(
            clex.calctype
        )

    def calc_settings_dir(self, clex: ClexDescription):
        """Return calculation settings directory path, for global settings from clex"""
        return (
            self.path
            / self.__calc_dir
            / self.__set_dir
            / self.__calctype(clex.calctype)
        )

    def calctype_settings_dir(self, calctype: str):
        """Return calculation settings directory path, for global settings from calctype"""
        return self.path / self.__calc_dir / self.__set_dir / self.__calctype(calctype)

    def supercell_calc_settings_dir(
        self,
        scelname: str,
        clex: ClexDescription,
        calc_subdir: str = "",
    ):
        """Return calculation settings directory path, for supercell specific settings"""
        return (
            self.supercell_dir(scelname, calc_subdir)
            / self.__set_dir
            / self.__calctype(clex.calctype)
        )

    def configuration_calc_settings_dir(
        self,
        configname: str,
        clex: ClexDescription,
        calc_subdir: str = "",
    ):
        """Return calculation settings directory path, for configuration specific settings"""
        return (
            self.configuration_dir(configname, calc_subdir)
            / self.__set_dir
            / self.__calctype(clex.calctype)
        )

    def calculated_properties(
        self,
        configname: str,
        clex: ClexDescription,
        calc_subdir: str = "",
    ):
        """Return calculated properties file path"""
        return (
            self.configuration_dir(configname, calc_subdir)
            / self.__calctype(clex.calctype)
            / "properties.calc.json"
        )

    def ref_dir(self, clex: ClexDescription):
        """Return calculation reference settings directory path, for global settings"""
        return self.calc_settings_dir(clex.calctype) / self.__ref(clex.ref)

    def composition_axes(self):
        """Return composition axes file path (deprecated v2.0a1)"""
        return self.casm_dir() / "composition_axes.json"

    def chemical_composition_axes(self):
        """Return chemical composition axes file path

        The `chemical_composition_axes` and `occupant_composition_axes` allow
        treating occupants that have the same chemical name but different
        magnetic spin, molecular orientation, etc. CASM v1 projects only
        have `composition_axes`.
        """
        return self.casm_dir() / "chemical_composition_axes.json"

    def occupant_composition_axes(self):
        """Return occupant composition axes file path

        The `chemical_composition_axes` and `occupant_composition_axes` allow
        treating occupants that have the same chemical name but different
        magnetic spin, molecular orientation, etc. CASM v1 projects only
        have `composition_axes`.
        """
        return self.casm_dir() / "occupant_composition_axes.json"

    def chemical_reference(self, clex: ClexDescription):
        """Return chemical reference file path"""
        return self.ref_dir(clex) / "chemical_reference.json"

    # -- Cluster expansions --------

    def property_dir(self, clex: ClexDescription):
        """Returns path to eci directory"""
        return self.path / self.__clex_dir / self.__clex_name(clex.property)

    def eci_dir(self, clex: ClexDescription):
        """
        Returns path to eci directory

        Parameters
        ----------
        clex: a casm.project.ClexDescription instance
            Specifies the cluster expansion to get the eci directory for

        Returns
        -------
        p: str
            Path to the eci directory
        """
        return (
            self.property_dir(clex)
            / self.__calctype(clex.calctype)
            / self.__ref(clex.ref)
            / self.__bset(clex.bset)
            / self.__eci(clex.eci)
        )

    def eci(self, clex: ClexDescription):
        """
        Returns path to eci.json

        Parameters
        ----------
        clex: a casm.project.ClexDescription instance
            Specifies the cluster expansion to get the eci.json for

        Returns
        -------
        p: str
            Path to the eci directory
        """
        return self.eci_dir(clex) / "eci.json"

    # -- Systems --------

    def system_dir(self, system: str):
        """Return path to directory contain system info"""
        return self.path / self.__system_dir / self.__system(system)

    # private:

    def __enum(self, enum: str):
        return "enum." + enum

    def __bset(self, bset: str):
        return "bset." + bset

    def __calctype(self, calctype: str):
        return "calctype." + calctype

    def __ref(self, ref: str):
        return "ref." + ref

    def __clex_name(self, clex_name: str):
        return "clex." + clex_name

    def __eci(self, eci: str):
        return "eci." + eci

    def __system(self, system: str):
        return "system." + system

    def __all_settings(self, pattern: str, location: pathlib.Path):
        """
        Find all directories at 'location' that match 'pattern.something'
        and return a std::vector of the 'something'
        """

        all = []
        pattern += "."

        # get all
        if not location.exists():
            return all

        for child in location.iterdir():
            if child.is_dir() and child.name[: len(pattern)] == pattern:
                all.append(child.name[len(pattern) :])
        return sorted(all)
