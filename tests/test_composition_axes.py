import io
from contextlib import redirect_stdout

from casm.project import Project


def test_ZrO_composition_axes_1(ZrO_tmp_project):
    project = ZrO_tmp_project

    f = io.StringIO()
    with redirect_stdout(f):
        print(project.chemical_composition_axes)
    out = f.getvalue()
    assert "0  Zr(2)O(2)   Zr(2)VaO  Zr(2)Va(a)O(2-a)" in out
    assert "1  Zr(2)Va(2)  Zr(2)VaO  Zr(2)Va(2-a)O(a)" in out
    assert "No composition axes selected" in out

    f = io.StringIO()
    with redirect_stdout(f):
        print(project.occupant_composition_axes)
    out = f.getvalue()
    assert "0  Zr(2)O(2)   Zr(2)VaO  Zr(2)Va(a)O(2-a)" in out
    assert "1  Zr(2)Va(2)  Zr(2)VaO  Zr(2)Va(2-a)O(a)" in out
    assert "No composition axes selected" in out


def test_ZrO_composition_axes_2(ZrO_tmp_project):
    project = ZrO_tmp_project

    ## Set current axes, but do not commit
    project.chemical_composition_axes.set_current_axes(1)

    f = io.StringIO()
    with redirect_stdout(f):
        print(project.chemical_composition_axes)
    out = f.getvalue()
    assert "0  Zr(2)O(2)   Zr(2)VaO  Zr(2)Va(a)O(2-a)" in out
    assert "1  Zr(2)Va(2)  Zr(2)VaO  Zr(2)Va(2-a)O(a)" in out
    assert "Currently selected composition axes: 1" in out
    assert "param_chem_pot(a) = chem_pot(O)" in out

    ## Then, current axes are not saved
    project_2 = Project.init(path=project.path)
    f = io.StringIO()
    with redirect_stdout(f):
        print(project_2.chemical_composition_axes)
    out = f.getvalue()
    print(out)
    assert "0  Zr(2)O(2)   Zr(2)VaO  Zr(2)Va(a)O(2-a)" in out
    assert "1  Zr(2)Va(2)  Zr(2)VaO  Zr(2)Va(2-a)O(a)" in out
    assert "No composition axes selected" in out

    ## Commit, then current axes are saved
    project.chemical_composition_axes.set_current_axes(1)
    project.chemical_composition_axes.commit()

    project_2 = Project.init(path=project.path)
    f = io.StringIO()
    with redirect_stdout(f):
        print(project_2.chemical_composition_axes)
    out = f.getvalue()
    print(out)
    assert "0  Zr(2)O(2)   Zr(2)VaO  Zr(2)Va(a)O(2-a)" in out
    assert "1  Zr(2)Va(2)  Zr(2)VaO  Zr(2)Va(2-a)O(a)" in out
    assert "Currently selected composition axes: 1" in out
    assert "param_chem_pot(a) = chem_pot(O)" in out
