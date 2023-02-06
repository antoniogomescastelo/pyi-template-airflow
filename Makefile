PORT := 8082
PROJECT := $(shell basename $(CURDIR))
VIRTUAL_ENVIRONMENT := $(CURDIR)/.venv
VIRTUAL_ENVIRONMENT_PYTHON := $(VIRTUAL_ENVIRONMENT)/bin/python

define HELP
Manage $(PROJECT). Usage:

make update                  - Update dependencies.
make install                 - Install the requirements.
make start-central-scheduler - Start luigi central scheduler.
make stop-central-scheduler  - Stop the luigi central scheduler.
make start-runner            - Run client either with the local or central scheduler.
make clean                   - Remove extraneous compiled files, caches, logs, etc.

endef
export HELP


.PHONY:  help update install start-central-scheduler stop-central-scheduler start-runner run-helper clean $(VIRTUAL_ENVIRONMENT)

.SILENT: help update install start-central-scheduler stop-central-scheduler start-runner run-helper clean $(VIRTUAL_ENVIRONMENT)


$(VIRTUAL_ENVIRONMENT):
	if [ ! -d $(VIRTUAL_ENVIRONMENT) ]; then \
		echo "Creating virtual environment in \`${VIRTUAL_ENVIRONMENT}\`"; \
		python -m venv $(VIRTUAL_ENVIRONMENT); \
	fi;

env: $(VIRTUAL_ENVIRONMENT)


help:
	@echo "$$HELP"


update: env
	echo Upgrading dependencies in \`${VIRTUAL_ENVIRONMENT}\` && \
	$(VIRTUAL_ENVIRONMENT_PYTHON) -m pip install --upgrade pip setuptools wheel;
	

install: env
	echo Installing requirements in \`${VIRTUAL_ENVIRONMENT}\` && \
	$(VIRTUAL_ENVIRONMENT_PYTHON) -m pip install -r requirements.txt;
	mkdir -p ./log
	mkdir -p ./output
	mkdir -p ./stage

start-central-scheduler: env
	echo Starting luigi central scheduler in port $(PORT) && \
	luigid --background --pidfile ./stage/luigi.pid --logdir ./log --port $(PORT);

stop-central-scheduler: env
	echo Stopping luigi central scheduler && \
	cat stage/luigi.pid|xargs kill -9;

start-runner: env
	python ./main.py --config ./config.toml --workers 1 

run-helper: env
	python ./helper.py --key $(key) --text $(text)

clean:
	echo Deleting extraneous files from \`$(CURDIR)\` && \
	find $(CURDIR) -type f -name '*.log' | xargs rm && \
	find $(CURDIR) -type f -name '*.err' | xargs rm && \
	find $(CURDIR) -type f -name '*.out' | xargs rm && \
	find $(CURDIR) -type f -name '.DS_Store' | xargs rm && \
	find $(CURDIR) -type d -name '__pycache__' | xargs rm -rf;
	find $(CURDIR)/stage -type f -name '*' | xargs rm ;
