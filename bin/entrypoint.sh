#!/usr/bin/env bash
set -e

sleep 10

application="$1"
command=(echo "Select one of: 'rhub-api', 'rhub-worker', 'rhub-cron'")

if [[ "$application" == 'rhub-api' ]]; then
  if [[ "$RHUB_SKIP_INIT" != 'True' ]]; then
    echo 'Calling flask initialization...'
    flask init
    echo 'Flask initialization finished.'
  fi

  command=(gunicorn -c config.py "${FLASK_APP}")

elif [[ "$application" == 'rhub-worker' ]]; then
  if [ ! -f "/opt/app-root/src/.ssh/id_rsa" ]; then
    # TODO: temporary solution. We need to find something that works for openshift and docker-compose (without swarm).
    # https://github.com/moby/moby/issues/40046
    echo "${RHUB_USER_SSH_KEY}" > /opt/app-root/src/.ssh/id_rsa

    chmod 600 /opt/app-root/src/.ssh/id_rsa
    chown 1001:0 /opt/app-root/src/.ssh/id_rsa

    printf "Host *.redhat.com\n\tStrictHostKeyChecking no\n" > /opt/app-root/src/.ssh/config
    chmod 644 /opt/app-root/src/.ssh/config
  fi

  # gets server name and port
  temp=(${RHUB_API_URL//\// })
  export FLASK_SERVER_NAME=${temp[1]}

  command=(celery -A rhub.api.celery_worker:celery worker --loglevel "${LOG_LEVEL:-INFO}")

elif [[ "$application" == 'rhub-cron' ]]; then
  mkdir -p ~/celery/

  command=(celery -A rhub.api.celery_worker:celery beat --schedule ~/celery/celerybeat-schedule --loglevel "${LOG_LEVEL:-INFO}")
fi

exec "${command[@]}"
