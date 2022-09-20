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
	pip-compile setup.py

.PHONY: scan clean_scan
scan: clean_scan
ifneq ($(GIT_ROOT), $(CURDIR))
    $(error Run make from git root -- $(GIT_ROOT))
endif
ifndef SONAR_TOKEN
	$(error SONAR_TOKEN needs to be defined to run the SonarScanner)
endif
	tox -e py3 -- --cov=src --cov-report=xml --cov-config=tox.ini --cov-branch tests
	sed -i 's#$(GIT_ROOT)#/usr/src#g' coverage.xml
	tox -e flake8 -- --color never --exit-zero --output-file=flake8_report.txt src
	tox -e bandit -- --exit-zero --format json --output bandit_report.json
	docker run \
	--rm \
	--pull always \
	-e SONAR_TOKEN \
	-v "$(GIT_ROOT):/usr/src:delegated,z" \
	-w /usr/src \
	images.paas.redhat.com/alm/sonar-scanner:latest \
	sonar-scanner \
	-Dproject.settings=sonar-project.properties

clean_scan:
	rm -f "$(GIT_ROOT)/coverage.xml" "$(GIT_ROOT)/flake8_report.txt" "$(GIT_ROOT)/bandit_report.json"
	coverage erase
