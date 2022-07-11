#!/usr/bin/env bash
set -e

cp /run/secrets/user_ssh_key /opt/app-root/src/.ssh/id_rsa
chmod 600 /opt/app-root/src/.ssh/id_rsa
chown 1001:0 /opt/app-root/src/.ssh/id_rsa

# gets server name and port
temp=(${RHUB_API_URL//\// })
export FLASK_SERVER_NAME=${temp[1]}

celery -A rhub.api.celery_worker:celery worker --uid 1001 --loglevel ${LOG_LEVEL:-INFO}
