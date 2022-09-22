GIT_ROOT := $(shell git rev-parse --show-toplevel)

default:

init:
	-cp -n .env.defaults .env
	-cp -n data/vault.example.yml data/vault.yml

build:
	docker build -t quay.io/resource-hub-dev/rhub-api --progress=plain .

build-no-cache:
	docker build -t quay.io/resource-hub-dev/rhub-api --progress=plain --no-cache .

down:
	docker-compose down -v

push:
	docker push quay.io/resource-hub-dev/rhub-api:latest

start:
	docker-compose up --force-recreate

stop:
	docker-compose down

test:
	tox

.PHONY: docs
docs:
	$(MAKE) -C docs html

.PHONY: clean
clean:
	$(MAKE) -C docs clean

requirements.txt: setup.py
	rm -f requirements.txt
	docker run \
	--rm \
	--pull always \
	-e USER \
	-u "$(id -u):$(id -g)" \
	-v "$(GIT_ROOT):/tmp/app" \
	-w /tmp/app \
	registry.access.redhat.com/ubi8/python-39 \
	/bin/bash -c 'pip install pip-tools && pip-compile'
