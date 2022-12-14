FROM registry.access.redhat.com/ubi8/python-39

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

USER 0

RUN dnf install openssh-clients; \
    dnf clean all

COPY . rhub_api
# https://docs.openshift.com/container-platform/4.11/openshift_images/create-images.html#images-create-guide-openshift_create-images
RUN ln -rsf rhub_api/bin bin && \
    chown -R 1001:0 . && chmod -R g=u,o-wX .

# "default" user in the ubi container
USER 1001

WORKDIR /opt/app-root/src/rhub_api/

# TODO: improve performance
RUN pip install -r requirements.txt -e .

RUN export RHUB_DB_TYPE='postgresql'; \
    export FLASK_ENV='development'; \
    export FLASK_APP='rhub.api:create_app()'; \
    export PROMETHEUS_MULTIPROC_DIR=/tmp/ ; \
    export RHUB_RETURN_INITIAL_FLASK_APP=True; \
    export RHUB_CONFIG=config/rhub.default.toml; \
    python3 -m flask routes;

ENTRYPOINT ["./bin/entrypoint.sh"]
CMD ["rhub-api"]

HEALTHCHECK --interval=10s --retries=5 --timeout=5s CMD ["./bin/healthcheck.sh", "rhub-api"]
