#!/usr/bin/env bash
set -e

application="$1"
command=(echo "Select one of: 'rhub-api', 'rhub-worker', 'rhub-cron'")

export RHUB_RETURN_INITIAL_FLASK_APP=true

if [[ "$application" == 'rhub-api' ]]; then
  command=(curl -f "http://localhost:${FLASK_RUN_PORT}/v0/ping")

elif [[ "$application" == 'rhub-worker' ]]; then
  export BROKER_URL=${RHUB_BROKER_TYPE}://${RHUB_BROKER_USERNAME}:${RHUB_BROKER_PASSWORD}@${RHUB_BROKER_HOST}:${RHUB_BROKER_PORT}
  command=(celery -A rhub.worker:celery inspect ping -d "celery@${HOSTNAME}")

elif [[ "$application" == 'rhub-cron' ]]; then
  # TODO: find a healthcheck
  exit 0
fi

exec "${command[@]}"
