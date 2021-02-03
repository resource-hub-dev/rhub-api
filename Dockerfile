# https://catalog.redhat.com/software/containers/ubi8/ubi/5c359854d70cc534b3a3784e
FROM registry.access.redhat.com/ubi8/ubi as base
RUN dnf module install -y python38
WORKDIR /opt/rhub-api
ENV PYTHONPATH=/opt/rhub-api/src:/opt/rhub-api/packages:$PYTHONPATH

FROM base
COPY . /opt/rhub-api
RUN pip3 install --upgrade -r ./requirements.txt -t ./packages
EXPOSE 80
CMD ["./bin/gunicorn"]
