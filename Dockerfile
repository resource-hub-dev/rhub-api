FROM registry.access.redhat.com/ubi8/python-39

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN dnf install openssh-clients; \
    dnf clean all

RUN mkdir -p ~/.ssh \
    && chmod 755 ~/.ssh

WORKDIR /opt/app-root/src/rhub_api/

USER 0
COPY . .
RUN /usr/bin/fix-permissions ./
# "default" user in the ubi container
USER 1001

# TODO: improve performance
RUN pip install -r requirements.txt -e .

RUN export RHUB_DB_TYPE='postgresql'; \
    export FLASK_ENV='development'; \
    export FLASK_APP='rhub.api:create_app()'; \
    export PROMETHEUS_MULTIPROC_DIR=/tmp/ ; \
    export RHUB_RETURN_INITIAL_FLASK_APP=True; \
    python3 -m flask routes;

ENTRYPOINT ["./bin/entrypoint.sh"]
CMD ["rhub-api"]

HEALTHCHECK --interval=10s --retries=5 --timeout=5s CMD ["./bin/healthcheck.sh", "rhub-api"]
