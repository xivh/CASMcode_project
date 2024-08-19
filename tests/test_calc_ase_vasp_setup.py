import os
import shutil

import casm.project.ase_utils as ase_utils


def test_ZrO_composition_axes_1(ZrO_tmp_project):
    project = ZrO_tmp_project
    enum_id = "occ_by_supercell.1"
    calctype_id = "vasp.default"

    project.enum.occ_by_supercell(
        max=3,
        min=1,
        id=enum_id,
    )

    enum_data = project.enum.get(enum_id)

    calctype_settings_dir = project.dir.calctype_settings_dir_v2(
        calctype="vasp.default",
    )
    files = os.listdir(calctype_settings_dir)
    assert "INCAR" in files
    assert "KPOINTS" in files

    x = ase_utils.AseVaspTool(
        calctype_settings_dir=calctype_settings_dir,
        setups={
            "Zr": "_sv",
            "O": "",
        },
        xc="pbe",
    )

    for record in enum_data.configuration_set:
        structure = record.configuration.to_structure()
        calc_dir = project.dir.enum_calctype_dir(
            enum=enum_id,
            configname=record.configuration_name,
            calctype=calctype_id,
        )
        x.setup(
            casm_structure=structure,
            calc_dir=calc_dir,
        )

        files = os.listdir(calc_dir)
        assert "POSCAR" in files
        assert "POTCAR" in files
        assert "INCAR" in files
        assert "KPOINTS" in files

    shutil.rmtree(project.dir.enum_dir(enum_id) / "training_data")
