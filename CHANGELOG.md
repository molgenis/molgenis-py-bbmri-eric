# Changelog

## Version 1.1.0 (development)

- Persistent Identifiers (PIDs) for biobanks
  - New biobanks are automatically assigned a PID
  - Biobank name changes are reflected in its PID record
  - Removal of a biobank is reflected in its PID record
- Removed command-line "eric" command
- Fixed issue #42 ID validation should not allow @ and .
- Fixed issue #43 Current ID validation results in false-positive invalid IDs

## Version 1.0.4

- Fixed issue #36 Deleted rows from a staging area are not deleted from the published ERIC tables
- Fixed issue #38 Parent and sub collections are empty in the ERIC collections table
- Fixed an issue where references were not validated correctly

## Version 1.0.3

- Fixed critical error when running on Python 3.6 or lower

## Version 1.0.2

- Fixed support for Python 3.6 by including the [dataclasses backport](https://pypi.org/project/dataclasses/)

## Version 1.0.1

- Adds library and command line tool for staging, validating, enriching and publishing national nodes of BBMRI-ERIC
