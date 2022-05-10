# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [0.1.7]
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
