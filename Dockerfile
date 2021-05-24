# https://catalog.redhat.com/software/containers/ubi8/python-38/5dde9cacbed8bd164a0af24a
FROM registry.access.redhat.com/ubi8/python-38
ENV PYTHONPATH=/opt/app-root/src/src:/opt/app-root/src/packages
COPY . .
RUN pip3 install --upgrade -r ./requirements.txt -t ./packages
CMD ["./bin/entrypoint.sh"]
