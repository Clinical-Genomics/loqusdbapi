# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [1.0]
### Added
- `/` endpoint is returning loqusdb version in use for this app
- `/cases` endpoint returning total number of cases with SNVs and SVs
- github action enforcing the update of a CHANGELOG
- Github actions to push repo images on Docker Hub
### Changed
- Renamed "nr_cases" to "total" in returned variant info
