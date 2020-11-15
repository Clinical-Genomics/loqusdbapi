# loqusdbapi

Small REST api to use with [loqusdb][loqusdb].

Currently only supports get requests for **variant**, **structural_variant** and **case**.

## Usage

### Running local installation


1. `git clone https://github.com/Clinical-Genomics/loqusdbapi`
1. `cd loqusdbapi`
1. `poetry install`
1. `uvicorn loqusdbapi.main:app --reload`

To use with `pip` the easy solution is to install [micropipenv][micropipenv] and generate a requirements file:

1. 

To run with Docker build the image with `docker build -t loqusapi .`

Then start a container called myapi listening on port 80 with `docker run -d --name myloqusapi -p 80:80 -e APP_MODULE="loqusdbapi.main:app" loqusapi`
  









[loqusdb]: https://github.com/moonso/loqusdb
[micropipenv]: 
