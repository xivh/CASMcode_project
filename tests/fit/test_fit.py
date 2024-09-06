from casm.project.fit import FittingData


def test_fit_0(ZrO_tmp_project):
    proj = ZrO_tmp_project
    fitting_data = proj.fit.get(id="0")
    assert isinstance(fitting_data, FittingData)
    assert fitting_data.fit_dir.exists() is False

    ## -- commit, no files --- ##
    fitting_data.commit()
    assert fitting_data.fit_dir.exists() is True
    contents = [file for file in fitting_data.fit_dir.iterdir()]
    assert len(contents) == 0

    ## -- commit, meta.json file --- ##
    fitting_data.meta["desc"] = "Fit 0"
    fitting_data.commit()
    assert fitting_data.fit_dir.exists() is True
    contents = [file for file in fitting_data.fit_dir.iterdir()]
    assert len(contents) == 1
