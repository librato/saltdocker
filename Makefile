install:
	pip install poetry
	poetry install

build:
	poetry run python -m saltdocker
	poetry run python -m saltdocker --push --dryrun
	pytest

push:
	docker login --username $(HUB_USERNAME) --password $(HUB_PASSWORD)
	poetry run python -m saltdocker --push --ecr=saltstack

pushecr:
	pip install -U awscli
	aws ecr get-login-password --region us-east-1 \
	  | docker login --username AWS  --password-stdin 377069709311.dkr.ecr.us-east-1.amazonaws.com
	poetry run python -m saltdocker --push --ecr=377069709311.dkr.ecr.us-east-1.amazonaws.com/sre/saltstack
