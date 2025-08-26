# Changelog

All notable changes to `casm-project` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added

- Added casm.project.DirectoryStructureV1 to separate CASM v1 project structure from CASM v2 project structure.

### Changed

- Changed casm.project.DirectoryStructure to remove CASM v1 project structure paths, change paths to v2 project locations, and to deprecate methods with `_v2` suffix.


## [2.0a1] - 2025-08-08

This release creates the casm-project package, which makes it easier to construct, fit, and use a cluster expansion in CASM version >= 2 by:

- providing quick access to the most commonly used methods,
- automatically reading project data needed by those methods from a CASM project directory,
- automatically writing the results to the standard location in a CASM project directory.

Using casm-project to store project data in standard locations makes it easier to understand what was done and share the project with others. 
