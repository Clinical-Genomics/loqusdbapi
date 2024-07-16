# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [0.1.14]
### Changed
- Updated issue template
### Fixed
- Update to setuptools >= v.70 to address a security issue in the package_index module

## [0.1.13]
### Fixed
- Fix chromosome name to "M" when user runs queries for "MT" variants on an database instance in build 38

## [0.1.12]
### Fixed
-  Modified Docker files to use python:3.9-slim-bullseye to prevent gunicorn workers booting error

## [0.1.11]
### Fixed
-  For compliance with latest MongoDB versions update loqusdb version to >=2.7.3 in requirements

## [0.1.10]
### Fixed
-  Introduce a "v" char before the numeric version tag that is pushed to Docker Hub prod when a new release is created

## [0.1.9]
### changed
- Unfreeze pymongo to support connections to new MongoDB software

## [0.1.8]
### Fixed
- Fix PyYaml installation error

## [0.1.7]
### Fixed
- Fix docker-compose file to mirror changes in Dockerfile (serve app via gunicorn)

## [0.1.3]
### Changed
- Use mongo_adapter 0.3.3 in frozen requirements file

## [0.1.2]
### Changed
- Use MongoDB v. 4.4.9 in docker-compose file

## [1.0]
### Added
- `/` endpoint is returning loqusdb version in use for this app
- `/cases` endpoint returning total number of cases with SNVs and SVs
- github action enforcing the update of a CHANGELOG
- Github actions to push repo images on Docker Hub
### Changed
- Renamed "nr_cases" to "total" in returned variant info
