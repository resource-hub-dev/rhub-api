#!/usr/bin/env bash
set -e

export PATH="./packages/bin:$PATH"

export RHUB_APP='rhub.api:create_app()'

if [[ $RHUB_SKIP_INIT != yes ]] ; then
    FLASK_APP="$RHUB_APP" \
        dockerize -wait tcp://$DB_HOST:$DB_PORT \
        python3 -m flask init
fi

exec dockerize \
    -wait tcp://$DB_HOST:$DB_PORT \
    -wait ${KEYCLOAK_SERVER}realms/$KEYCLOAK_REALM \
    gunicorn --bind 0.0.0.0:8081 --log-level ${LOG_LEVEL:-info} "$RHUB_APP"
