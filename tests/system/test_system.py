from casm.project.system import SystemData


def test_system_0(ZrO_tmp_project):
    proj = ZrO_tmp_project
    system_data = proj.system.get(id="0")
    assert isinstance(system_data, SystemData)
    assert system_data.system_dir.exists() is False

    ## -- commit, no files --- ##
    system_data.commit()
    assert system_data.system_dir.exists() is True
    contents = [file for file in system_data.system_dir.iterdir()]
    assert len(contents) == 0

    ## -- commit, meta.json file --- ##
    system_data.meta["desc"] = "System 0"
    system_data.commit()
    assert system_data.system_dir.exists() is True
    contents = [file for file in system_data.system_dir.iterdir()]
    assert len(contents) == 1
