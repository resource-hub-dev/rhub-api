#!/usr/bin/env bash
set -e

mkdir /var/run/celery/

celery -A rhub.api.celery_worker:celery beat --schedule=/var/run/celery/celerybeat-schedule --loglevel ${LOG_LEVEL:-INFO}
