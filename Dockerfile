# https://catalog.redhat.com/software/containers/ubi8/ubi/5c359854d70cc534b3a3784e
FROM registry.access.redhat.com/ubi8/ubi
RUN dnf module install -y python38
COPY . /opt/rhub-api
WORKDIR /opt/rhub-api
RUN pip3 install --upgrade -r ./requirements.txt
ENV PYTHONPATH=/opt/rhub-api/src:$PYTHONPATH
EXPOSE 80
CMD ["./bin/gunicorn"]
