def test_merge(SiGe_occ_tmp_project):
    project = SiGe_occ_tmp_project

    enum_1 = project.enum.get("1")
    enum_1.occ_by_supercell(
        min=2,
        max=2,
    )
    enum_1.commit()
    # print("enum_1 configurations:")
    # for record in enum_1.configuration_set:
    #     config = record.configuration
    #     configuration_name = record.configuration_name
    #     print(f"{configuration_name}: {config.occupation.tolist()}")
    # print()

    assert len(enum_1.configuration_set) == 7

    # copy configurations:
    enum_2 = project.enum.get("2")
    for record in enum_1.configuration_set:
        enum_2.configuration_set.add(record.configuration)
    enum_2.commit()
    assert len(enum_2.configuration_set) == 7

    # discard some configurations from enum_1:
    enum_1.configuration_set.discard_by_name("SCEL2_2_1_1_0_1_1/0")
    enum_1.configuration_set.discard_by_name("SCEL2_2_1_1_0_1_1/1")
    enum_1.commit()
    assert len(enum_1.configuration_set) == 5

    # get the remaining configurations and names:
    before = []
    for record in enum_1.configuration_set:
        before.append((record.configuration_name, record.configuration.copy()))

    # merge 2 into 1:
    enum_1.merge(enum_2)
    enum_1.commit()
    assert len(enum_1.configuration_set) == 7

    # check that the configurations in enum_1 are the same as before the merge:
    for name, config in before:
        found = False
        for record in enum_1.configuration_set:
            if record.configuration_name == name:
                assert (
                    record.configuration == config
                ), f"Configuration {name} does not match after merge"
                found = True
                break
        assert found, f"Configuration {name} not found after merge"
