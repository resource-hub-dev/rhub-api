# https://catalog.redhat.com/software/containers/ubi8/python-38/5dde9cacbed8bd164a0af24a
FROM registry.access.redhat.com/ubi8/python-38

ENV PYTHONPATH=/opt/app-root/src/src:/opt/app-root/src/packages
COPY . .
RUN pip3 install --upgrade -r ./requirements.txt -t ./packages

USER 0

ENV DOCKERIZE_VERSION v0.6.1
RUN wget -q https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

# "default" user in the ubi container
USER 1001

CMD ["./bin/entrypoint.sh"]
