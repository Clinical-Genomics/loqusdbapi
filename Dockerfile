FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

RUN pip install -U pip


RUN pip install micropipenv[toml] numpy cython

# Copy the lockfile to temporary directory. This will be deleted
COPY ./pyproject.toml ./poetry.lock /app/
# Generate reqs with locked dependencies for deterministic build
RUN cd /app && micropipenv requirements --method poetry > requirements.txt
# Install deps
RUN pip install -r /app/requirements.txt

# Copy package
COPY . /app
