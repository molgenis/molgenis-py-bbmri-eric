# Changelog
## Version 1.5.0 (development)
- Adds step to fill combined_network field
- Fix issue #61, import of NL data fails due to self-referencing columns

## Version 1.4.0
- PIDs are prefixed with `1.` (example: `1.6ed7-328b-2793`)

## Version 1.3.0
- The PID feature can be turned off completely by supplying a NoOpPidService

## Version 1.2.1
- PID URLs are based on a config parameter instead of the session

## Version 1.2.0
- Change PID format to use a random 12 digit hexadecimal number (example: `6ed7-328b-2793`)
- Introduced a DummyPidService to test publishing without interacting with a Handle server
- Fixed issue #35 References to EU networks and persons don't pass validation
- Fixed issue #41 Rows of node EU are overwritten by other nodes that reference them

## Version 1.1.0

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
