COMPOSE_RUN?=docker compose run --rm ansible
COMPOSE_RUN_PLAYBOOK?=$(COMPOSE_RUN) ansible-playbook

help:
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n"} /^[$$()% 0-9a-zA-Z_-]+:.*?##/ { printf "    \033[32m%-30s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m:\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Base
build: ## Собрать контейнер
	COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker compose build

run: __opts-param ## Запустить playbook
	$(COMPOSE_RUN_PLAYBOOK) $(opts) $(if $(limit),--limit $(limit),)

setup: ## Setup хостов
	$(COMPOSE_RUN_PLAYBOOK) setup.yml $(opts) $(if $(limit),--limit $(limit),)

caddy: ## Развернуть caddy
	$(COMPOSE_RUN_PLAYBOOK) caddy.yml $(opts) $(if $(limit),--limit $(limit),)

##@ 3X
3x-ui: ## Развернуть 3x-ui
	$(COMPOSE_RUN_PLAYBOOK) 3x-ui.yml $(opts) $(if $(limit),--limit $(limit),)

__pass-param:
	@[ ! -z '$(pass)' ] || (echo "Error: pass param required"; exit 1)

__new-param:
	@[ ! -z '$(new)' ] || (echo "Error: new param required"; exit 1)

__opts-param:
	@[ ! -z '$(opts)' ] || (echo "Error: opts param required"; exit 1)

__val-param:
	@[ ! -z '$(val)' ] || (echo "Error: val param required"; exit 1)

__name-param:
	@[ ! -z '$(name)' ] || (echo "Error: name param required"; exit 1)

__path-param:
	@[ ! -z '$(path)' ] || (echo "Error: path param required"; exit 1)
