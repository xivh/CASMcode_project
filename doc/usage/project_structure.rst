
.. _project-structure-v2:
.. _project-structure-latest:

CASM Project Structure (v2 / latest)
====================================

The CASM project structure standardizes the location of various files used by CASM.

For the project structure in previous versions, see:

- :ref:`CASM Project Structure (v1) <project-structure-v1>`

Path variable convention
------------------------

In the descriptions that follow, some name or paths include codes of the form *<variable>* to indicate that there are multiple files or directory paths with varying names but following the same pattern.

Path variables include:

- *<project>*: The root CASM project directory
- *<configname>*: The name of a configuration.
- *<title>*: The CASM project title, as given in the *prim.json* file used to initialize it.
- *<dof_key>*: The name of a type of degrees of freedom (DoF), as listed in *prim.json*.
- *<enum>*: Enumeration directory, ex: *<enum> = 'enum.main'*.
- *<bset>*: Basis set directory, ex: *<bset> = 'bset.chebychev'*.
- *<calctype>*: Calculation settings directory, Ex: *<calctype> = 'calctype.vasp_gga'*.
- *<ref>*: Reference states directory, ex: *<ref> = 'ref.1'*.
- *<eci>*: Fitting coefficients (effective cluster interactions) directory, ex: *<eci> = 'eci.1'*.


CASM project directories
------------------------

.. raw:: html

    <style>

        .casm-part {
            margin-bottom: 10px;
        }

        dl.casm-list div dd {
          margin-left: 0 !important;
          margin-inline-start: 0px !important;
        }

        .casm-part code{
            padding: 0px 10px;
        }

        .casm-table th, .casm-table td {
            padding-left: 10px;
            padding-right: 0px;
            border: 1px solid #ddd;
            font-size: 1em;
        }
        .casm-table {
            border-collapse: collapse;
            width: 100%;
        }
    </style>

.. include:: project_structure_tables.rst

