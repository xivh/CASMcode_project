import io
import time
from contextlib import redirect_stdout

import numpy as np

import casm.project
import libcasm.clexulator


def test_bset_periodic_1(SiGe_occ_tmp_project):
    project = SiGe_occ_tmp_project
    assert isinstance(project, casm.project.Project)

    project.sym.print_factor_group()

    # Specify the basis set ID
    # - Must be alphanumeric and underscores only
    bset_id = "default"

    ## Construct the basis set specs ##

    # Specify maximum cluster site-to-site distance,
    # by number of sites in the cluster
    pair_max_length = 10.01
    triplet_max_length = 7.27
    quad_max_length = 4.0

    # Use chebychev site basis functions (+x, -x)
    occ_site_basis_functions_specs = "occupation"

    bset = project.bset.get(bset_id)
    bset.make_bspecs(
        max_length=[
            0.0,  # null cluster, arbitrary
            0.0,  # point cluster, arbitrary
            pair_max_length,
            triplet_max_length,
            quad_max_length,
        ],
        occ_site_basis_functions_specs=occ_site_basis_functions_specs,
    )
    bset.commit()
    assert project.dir.bspecs(bset=bset_id).exists()
    assert not project.dir.clexulator_src(
        projectname=project.name, bset=bset_id
    ).exists()

    ## Set meta data ##
    bset.meta["desc"] = "Chebychev basis set"
    bset.commit()

    ## Print ##
    f = io.StringIO()
    with redirect_stdout(f):
        print(bset)
    out = f.getvalue()
    print(out)
    assert "id" in out
    assert "n_functions" not in out

    ## Write and compile the clexulator ##

    start = time.time()
    bset.update(no_compile=True)
    bset.update(only_compile=True)
    assert project.dir.clexulator_src(projectname=project.name, bset=bset_id).exists()
    elapsed = time.time() - start
    print(f"elapsed time: {elapsed}")

    ## Get the clexulator ##
    start = time.time()
    clexulator = bset.make_clexulator()
    assert isinstance(clexulator, libcasm.clexulator.Clexulator)
    elapsed = time.time() - start
    print(f"elapsed time: {elapsed}")

    ## Print ##
    f = io.StringIO()
    with redirect_stdout(f):
        print(bset)
    out = f.getvalue()
    print(out)
    assert "id" in out
    assert "n_functions" in out
    assert "n_variables" in out
    assert "n_update_neighborhood_sites" in out

    ## Enum ##
    enum_id = "occ_by_supercell.1"
    enum = project.enum.get(enum_id)
    enum.occ_by_supercell(max=4)

    ## Evaluate correlations
    corr = bset.make_corr_calculator().per_unitcell(enum.configuration_set)
    assert isinstance(corr, np.ndarray)
    assert corr.shape[0] == len(enum.configuration_set)
    assert corr.shape[1] == clexulator.n_functions()
    print(corr)
    print()

    ## Clean up ##
    bset.clean()

    ## Print ##
    f = io.StringIO()
    with redirect_stdout(f):
        print(bset)
    out = f.getvalue()
    print(out)
    assert "id" in out
    assert "n_functions" not in out
