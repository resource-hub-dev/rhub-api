default:

init:
	-cp -n .env.defaults .env

build:
	docker build -t quay.io/resource-hub-dev/rhub-api --no-cache --force-rm .
	-docker rm -f rhub-api
	docker run -d --env-file .env.defaults -e RHUB_SKIP_INIT=yes --name rhub-api quay.io/resource-hub-dev/rhub-api
	sleep 10
	docker logs rhub-api
	docker run --rm --network container:rhub-api curlimages/curl -f http://localhost:8081/v0/cowsay
	docker rm -f rhub-api

install:
	docker-compose run --rm api pip3 install --upgrade -r ./requirements.txt -t ./packages

start:
	docker-compose up --force-recreate
