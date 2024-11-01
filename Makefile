# SPDX-License-Identifier:  CC-BY-SA-4.0

PYTHON := python3

ARGS := ""
ifneq (,$(args))
	ARGS := $(args)
endif

SIMULATIONS = pi_controller http_balancer http_server timed_net
GRAPHS = $(patsubst %,src/%/graph.gv,$(SIMULATIONS))
GRAPHS_PIX = $(patsubst %,src/%/graph.png,$(SIMULATIONS))

all:
ifneq (,$(strip $(run)))
	$(PYTHON) -m "src.$(run)" main $(ARGS)
else ifneq (,$(strip $(results)))
	$(PYTHON) -m "src.$(results)" results $(ARGS)
else ifneq (,$(strip $(graph)))
	$(PYTHON) -m "src.$(graph)" graph $(ARGS)
else ifneq (,$(strip $(build)))
	pip install -r "src/$(build)/requirements.txt"
else ifneq (,$(strip $(clean)))
	$(PYTHON) -m "src.$(clean)" clean $(ARGS)
endif

.SECONDEXPANSION:
$(GRAPHS): src/%/graph.gv: $$(wildcard src/%/*.py)
	$(PYTHON) -m src.$(subst /graph.gv,,$(subst src/,,$@)) graph

$(SIMULATIONS): ;

$(GRAPHS_PIX): src/%/graph.png: src/%/graph.gv
	dot -Tpng $? > $@

graphs: $(GRAPHS_PIX)

compile:
	sphinx-apidoc -o docs/source/ src/
	cd docs && make html

docs: dev-build graphs compile

build:
	pip install -r requirements.txt

dev-build: build
	pip install -r dev-requirements.txt
	black --line-length 88 --target-version py310 --exclude 'venv\/.*\.pyi?$$' .

run-all: $(SIMULATIONS)
	@echo "`tput bold`Running: $<`tput sgr0`"
	pip install -r "src/$</requirements.txt"
	$(PYTHON) -m src.$< main $(ARGS)

results-all: $(SIMULATIONS)
	@echo "`tput bold`Results for: $<`tput sgr0`"
	pip install -r "src/$</requirements.txt"
	$(PYTHON) -m src.$< results $(ARGS)

.PHONY: all $(SIMULATIONS)
