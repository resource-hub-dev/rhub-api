#!/usr/bin/env bash
set -e

sleep 10

if [[ $RHUB_SKIP_INIT != "True" ]]; then
    echo 'Calling flask initialization...'
    flask init
    echo 'Flask initialization finished.'
fi

gunicorn -c config.py "$FLASK_APP"

