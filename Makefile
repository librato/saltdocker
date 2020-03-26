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

# Put the ECR repo into an environment variable called ECR
pushecr:
	pip install -U awscli
	aws ecr get-login-password --region us-east-1 \
	  | docker login --username AWS  --password-stdin $$ECR 
	poetry run python -m saltdocker --push --ecr
