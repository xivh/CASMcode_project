#### CASM prim files

This directory holds example CASM "prim" files for testing purposes. 

#### Ordered prim

The subdirectory "ordered" holds prim in which the lattice parameters and basis site coordinates match those of a high symmetry parent crystal structure, but either (i) there is a different default occupant on otherwise symmetrically equivalent sublattices, or (ii) there are different sets of allowed occupants on otherwise symmetrically equivalent sublattices. 

Unless explicitly restricted using "labels" to distinguish basis sites, CASM will generate a factor group that includes symmetry operations that map sites that have the same set of allowed occupants, even if they are listed in a different order. Listing occupants in different orders may restrict which type of site basis functions can be used.