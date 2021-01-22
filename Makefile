default:

build:
	docker build -t quay.io/resource-hub-dev/rhub-api --no-cache --force-rm .
	docker rm -f rhub-api || :
	docker run --rm -d --name rhub-api quay.io/resource-hub-dev/rhub-api
	sleep 5
	docker run --rm --link rhub-api curlimages/curl -sf rhub-api/cowsay
	docker rm -f rhub-api

install:
	docker-compose run --rm api pip3 install --upgrade -r ./requirements.txt -t ./packages

start:
	docker-compose up --force-recreate
