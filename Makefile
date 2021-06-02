default:

init:
	-cp -n .env.defaults .env
	-cp -n data/vault.example.yml data/vault.yml

build:
	docker build -t quay.io/resource-hub-dev/rhub-api --no-cache --force-rm .
	@# Simple sanity check.
	docker run --rm \
		--env-file .env.defaults \
		-e RHUB_SKIP_INIT=yes \
		-e FLASK_APP='rhub.api:create_app()' \
		quay.io/resource-hub-dev/rhub-api \
		python3 -m flask routes

install:
	docker-compose run --rm api pip3 install --upgrade -r ./requirements.txt -t ./packages

start:
	docker-compose up --force-recreate
