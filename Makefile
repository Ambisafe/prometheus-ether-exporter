.PHONY: help clean clean-docker-image docker-image local-ethexporter
.DEFAULT_GOAL := help

name = ambisafe1/prometheus-ether-exporter
version ?= latest


define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
    match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
    if match:
       target, help = match.groups()
       print("%-20s: %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)


clean: clean-docker-image ## clean all


clean-docker-image: ## remove docker image(s) for current version
	docker rmi ${name}:${version}


docker-image: ## build image(s) for local geth ethereum network
	$(call _echo_blue, "Building docker image...")
	docker build -t ${name}:${version} -f Dockerfile .


local-ethexporter: docker-image-geth ## start local geth ethereum network
	docker-compose -f docker-compose.gethinx-parity.yml up -d


define _echo_blue
	@tput setaf 6
	@echo $1
	@tput sgr0
endef
