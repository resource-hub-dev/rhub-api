#!/usr/bin/env bash
set -e

echo "Waiting for keycloak..."
CURL_OPTS='--retry 10 --retry-delay 6 --retry-connrefused -sSf'
curl $CURL_OPTS http://keycloak:8080 2>&1 > /dev/null

if [[ $RHUB_SKIP_INIT != "True" ]]; then
    echo 'Calling flask initialization...'
    flask init
    echo 'Flask initialization finished.'
fi

gunicorn -c config.py "$FLASK_APP"

