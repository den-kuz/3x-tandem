$(shell touch ./env/.env)
COMPOSE_RUN?=docker compose run --rm --env-from-file ./env/.env --env-from-file ./env/.env.example ansible
COMPOSE_RUN_PLAYBOOK?=$(COMPOSE_RUN) ansible-playbook

help:
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n"} /^[$$()% 0-9a-zA-Z_-]+:.*?##/ { printf "    \033[32m%-30s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m:\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Base
build: ## Собрать контейнер
	COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker compose build

run: __opts-param ## Запустить playbook
	$(COMPOSE_RUN_PLAYBOOK) $(opts) $(if $(limit),--limit $(limit),)

setup: ## Setup хостов
	$(COMPOSE_RUN_PLAYBOOK) setup.yml $(opts) $(if $(limit),--limit $(limit),) $(if $(tag),-t $(tag),) $(if $(regenerate_db),-e regenerate_db=1,)

__opts-param:
	@[ ! -z '$(opts)' ] || (echo "Error: opts param required"; exit 1)
