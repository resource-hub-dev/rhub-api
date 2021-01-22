default:

install:
	docker-compose run --rm api pip3 install --upgrade -r ./requirements.txt -t ./packages

start:
	docker-compose up --force-recreate
