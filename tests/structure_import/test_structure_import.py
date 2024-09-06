from casm.project.structure_import import StructureImportData


def test_structure_import_0(ZrO_tmp_project):
    proj = ZrO_tmp_project
    structure_import = proj.structure_import.get(id="0", enum_id="0")
    assert isinstance(structure_import, StructureImportData)
    print(structure_import.enum.enum_dir)
    assert structure_import.import_dir.exists() is False
    assert structure_import.enum.enum_dir.exists() is False

    ## -- commit, no files --- ##
    structure_import.commit()
    assert structure_import.import_dir.exists() is True
    contents = [file for file in structure_import.import_dir.iterdir()]
    assert len(contents) == 0

    assert structure_import.enum.enum_dir.exists() is True
    contents = [file for file in structure_import.enum.enum_dir.iterdir()]
    assert len(contents) == 0

    ## -- commit, meta.json file --- ##
    structure_import.meta["desc"] = "Structure import 0"
    structure_import.commit()
    assert structure_import.import_dir.exists() is True
    contents = [file for file in structure_import.import_dir.iterdir()]
    assert len(contents) == 1

    assert structure_import.enum.enum_dir.exists() is True
    contents = [file for file in structure_import.enum.enum_dir.iterdir()]
    assert len(contents) == 0
