default:

build:
	docker build -t quay.io/resource-hub-dev/rhub-api --no-cache --force-rm .
	docker rm -f rhub-api || :
	docker run -d --name rhub-api quay.io/resource-hub-dev/rhub-api
	sleep 10
	docker logs rhub-api
	docker run --rm --network container:rhub-api curlimages/curl -f http://localhost/cowsay
	docker rm -f rhub-api

	# export COMPOSE_FILE=./docker-compose.build.yml
	# docker-compose build --no-cache --force-rm
	# docker-compose up -d --force-recreate
	# sleep 5
	# docker-compose logs
	# docker-compose run --rm curl -f http://api/cowsay
	# docker-compose down

install:
	docker-compose run --rm api pip3 install --upgrade -r ./requirements.txt -t ./packages

start:
	docker-compose up --force-recreate
