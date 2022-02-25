FROM registry.access.redhat.com/ubi8/python-39

ENV PATH "$PATH:/opt/app-root/packages/bin/"
ENV PYTHONPATH=/opt/app-root/src/src:/opt/app-root/packages

COPY ./requirements.txt ./requirements.txt
RUN pip3 install pip-tools && pip-sync --pip-args '-t ../packages'
COPY . .

USER 0

RUN chown -R 1001:0 /opt/app-root

# "default" user in the ubi container
USER 1001

WORKDIR /opt/app-root/src/

RUN export RHUB_DB_TYPE='postgresql'; \
    export FLASK_ENV='development'; \
    export FLASK_APP='rhub.api:create_app()'; \
    export PROMETHEUS_MULTIPROC_DIR=/tmp/ ; \
    export PYTHONPATH=/opt/app-root/src/src:/opt/app-root/src/src/rhub:/opt/app-root/packages \
    export RHUB_RETURN_INITIAL_FLASK_APP=True; \
    python3 -m flask routes;

CMD ["./bin/entrypoint.sh"]

HEALTHCHECK --interval=10s --retries=5 --timeout=5s CMD ["curl", "-f", "http://localhost:8081/v0/ping"]
