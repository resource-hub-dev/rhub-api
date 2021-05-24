#!/usr/bin/env sh
set -e

export PATH="./packages/bin:$PATH"

export RHUB_APP='rhub.api:create_app()'

[[ $RHUB_SKIP_INIT = yes ]] \
    || FLASK_APP="$RHUB_APP" python3 -m flask init

exec gunicorn --bind 0.0.0.0:8081 "$RHUB_APP"
