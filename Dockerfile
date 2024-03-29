FROM python:3.9-slim-bullseye

ENV GUNICORN_WORKERS=1
ENV GUNICORN_THREADS=1
ENV GUNICORN_BIND="0.0.0.0:8000"
ENV GUNICORN_TIMEOUT=400
ENV URI="mongodb://localhost:27017/loqusdb"
ENV DB_NAME="loqusdb"


ENV GENOME_BUILD="GRCh37"
ENV LOAD_GQ_THRESHOLD=20
ENV LOAD_HARD_THRESHOLD=0.95
ENV LOAD_SOFT_THRESHOLD=0.95
ENV LOAD_SV_WINDOW=2000
ENV CYVCF_THREADS=4

WORKDIR /home/app
COPY . /home/app

RUN apt-get -y update
RUN apt-get -y install build-essential python3-dev openssl autoconf automake make gcc perl zlib1g-dev libbz2-dev liblzma-dev libcurl4-gnutls-dev libssl-dev libncurses5-dev samtools

RUN pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir


CMD gunicorn \
    --workers=$GUNICORN_WORKERS \
    --bind=$GUNICORN_BIND  \
    --threads=$GUNICORN_THREADS \
    --timeout=$GUNICORN_TIMEOUT \
    --proxy-protocol \
    --forwarded-allow-ips="10.0.2.100,127.0.0.1" \
    --log-syslog \
    --access-logfile - \
    --error-logfile - \
    --log-level="debug" \
    --worker-class=uvicorn.workers.UvicornWorker \
    loqusdbapi.main:app
