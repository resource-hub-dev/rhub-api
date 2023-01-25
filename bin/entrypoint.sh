#!/usr/bin/env bash
set -e

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
    mkdir -p /opt/app-root/src/.ssh
    chmod 755 /opt/app-root/src/.ssh

    # TODO: temporary solution. We need to find something that works for openshift and docker-compose (without swarm).
    # https://github.com/moby/moby/issues/40046
    echo "${RHUB_USER_SSH_KEY}" > /opt/app-root/src/.ssh/id_rsa

    chmod 600 /opt/app-root/src/.ssh/id_rsa

    printf "Host *.redhat.com\n\tStrictHostKeyChecking no\n" > /opt/app-root/src/.ssh/config
    chmod 644 /opt/app-root/src/.ssh/config
  fi

  # gets server name and port
  temp=(${RHUB_API_URL//\// })
  export FLASK_SERVER_NAME=${temp[1]}

  command=(celery -A rhub.worker:celery worker --loglevel "${LOG_LEVEL:-INFO}" --concurrency "${CELERY_CONCURRENCY:-1}")

elif [[ "$application" == 'rhub-cron' ]]; then
  mkdir -p $RHUB_DATA_DIR/celery/

  command=(celery -A rhub.worker:celery beat --schedule $RHUB_DATA_DIR/celery/celerybeat-schedule --loglevel "${LOG_LEVEL:-INFO}")
fi

exec "${command[@]}"
