#!/usr/bin/env bash

# Based on: https://github.com/jeremylong/DependencyCheck#docker

set -e

DC_VERSION="latest"
DC_DIRECTORY=/tmp/OWASP-Dependency-Check
CACHE_DIRECTORY="$DC_DIRECTORY/data/cache"
DATA_DIRECTORY="$DC_DIRECTORY/data"
GIT_ROOT=$(git rev-parse --show-toplevel)
REPORT_DIRECTORY="$GIT_ROOT/odc-reports"
VENV_DIRECTORY=$(mktemp -d)

for directory in "$DATA_DIRECTORY" "$CACHE_DIRECTORY" "$REPORT_DIRECTORY"; do
  mkdir -p "$directory"
done

# Create a virtual env in a temp dir to have only the dependencies installed, to do a proper scanning.
python -m venv "$VENV_DIRECTORY"
. "$VENV_DIRECTORY/bin/activate"
pip install -U pip setuptools wheel
pip install -r "$GIT_ROOT/requirements.txt"

docker run \
  --rm \
  --pull always \
  -e USER \
  -u "$(id -u):$(id -g)" \
  --volume "$VENV_DIRECTORY":/src:z \
  --volume "$DATA_DIRECTORY":/usr/share/dependency-check/data:z \
  --volume "$REPORT_DIRECTORY":/report:z \
  owasp/dependency-check:"$DC_VERSION" \
  --enableExperimental \
  --scan /src \
  --format "ALL" \
  --project "rhub-api" \
  --out /report

deactivate
rm -rf "$VENV_DIRECTORY"
