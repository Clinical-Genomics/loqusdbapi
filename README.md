# loqusdbapi

Small REST api to use with [loqusdb][loqusdb].

Currently only supports get requests for **variant**, **structural_variant** and **case**.

# Usage

## Running local installation

### poetry

1. `git clone https://github.com/Clinical-Genomics/loqusdbapi`
1. `cd loqusdbapi`
1. `poetry install`
1. `uvicorn loqusdbapi.main:app --reload`

### pip
To use with `pip` the easy solution is to install [micropipenv][micropipenv] and generate a requirements file:

1. `pip install micropipenv[toml]`
1. `micropipenv requirements --method poetry > requirements.txt`
1. `pip install -r requirements.txt`
1. `uvicorn loqusdbapi.main:app --reload`

Go to `http://127.0.0.1:8000/docs`

### docker
To run with Docker build the image with `docker build -t loqusapi .`

Then start a container called myapi listening on port 80 with `docker run -d --name myloqusapi -p 8000:80 -e APP_MODULE="loqusdbapi.main" loqusapi`

Head over to `http://127.0.0.1:8000/docs`

## Setup a test case with some data using docker compose

1. `docker-compose up`
1. Port `80` is mapped to `9000` in the docker compose file so go to `http://127.0.0.1:9000/docs`
1. Fetch a variant with `curl -X GET "http://127.0.0.1:9000/variants/1_880086_T_C" -H  "accept: application/json"`


[loqusdb]: https://github.com/moonso/loqusdb
[micropipenv]: https://github.com/thoth-station/micropipenv
