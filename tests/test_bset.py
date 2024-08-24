import casm.project


def test_bset_make_bspecs_1(SiGe_occ_tmp_project):
    project = SiGe_occ_tmp_project
    assert isinstance(project, casm.project.Project)

    project.sym.print_factor_group()

    # Specify the basis set ID
    # - Must be alphanumeric and underscores only
    bset_id = "default"

    # Specify maximum cluster site-to-site distance,
    # by number of sites in the cluster
    pair_max_length = 10.01
    triplet_max_length = 7.27
    quad_max_length = 4.0

    # Use chebychev site basis functions (+x, -x)
    occ_site_basis_functions_specs = "chebychev"

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
