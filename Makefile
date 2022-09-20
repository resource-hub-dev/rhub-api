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
	pip-compile setup.py

.PHONY: scan
scan:
ifndef SONAR_TOKEN
	$(error SONAR_TOKEN needs to be defined to run the SonarScanner)
endif
	$(eval GIT_ROOT := $(shell git rev-parse --show-toplevel))
	rm -f "$(GIT_ROOT)/coverage.xml"
	tox -e py3 -- --cov=src --cov-report=xml --cov-config=tox.ini --cov-branch tests
	sed -i 's#$(GIT_ROOT)#/usr/src#g' coverage.xml
	docker run \
	--rm \
	--pull always \
	-e SONAR_TOKEN \
	-v "$(GIT_ROOT):/usr/src:delegated,z" \
	-w /usr/src \
	images.paas.redhat.com/alm/sonar-scanner:latest \
	sonar-scanner \
	-Dproject.settings=sonar-project.properties
