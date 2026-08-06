PYTHON ?= python3
CONFIG ?= simulation/configs/minimal.json
REFERENCE_DIR ?= artifacts/reference_run
SMOKE_DIR ?= .tmp/smoke
EPISODES ?= 64
SEED ?= 7

.PHONY: help materialize explain compile test smoke experiment verify-artifact verify paper paper-clean clean

help:
	@printf '%s\n' \
	  'Nashs Cage / RVCIM commands' \
	  '' \
	  '  make verify           Compile-check, test, and run a verified smoke experiment' \
	  '  make experiment       Generate the complete four-arm reference experiment' \
	  '  make materialize      Expand hash-verified Python, TeX, and bibliography sources' \
	  '  make explain          Print the F0 claim boundary and paper-to-code map' \
	  '  make test             Run the standard-library unit tests' \
	  '  make paper            Materialize and build manuscript v0.2' \
	  '  make verify-artifact  Verify a generated reference receipt when present' \
	  '  make clean            Remove local smoke and TeX build products'

materialize:
	$(PYTHON) .bootstrap/assemble.py

explain:
	$(PYTHON) -m simulation explain

compile:
	$(PYTHON) -m py_compile simulation/__init__.py simulation/__main__.py simulation/rvcim_sim.py

test:
	$(PYTHON) -m unittest discover -s simulation/tests -v

smoke:
	rm -rf $(SMOKE_DIR)
	$(PYTHON) -m simulation smoke --config $(CONFIG) --episodes 4 --seed 101 --out $(SMOKE_DIR)
	$(PYTHON) -m simulation verify --receipt $(SMOKE_DIR)/receipt.json

experiment:
	$(PYTHON) -m simulation run --config $(CONFIG) --episodes $(EPISODES) --seed $(SEED) --out $(REFERENCE_DIR) --overwrite
	$(PYTHON) -m simulation verify --receipt $(REFERENCE_DIR)/receipt.json

verify-artifact:
	@if [ -f "$(REFERENCE_DIR)/receipt.json" ]; then \
	  $(PYTHON) -m simulation verify --receipt "$(REFERENCE_DIR)/receipt.json"; \
	else \
	  printf '%s\n' 'No committed reference receipt yet; run `make experiment` to create one.'; \
	fi

verify: compile test smoke

paper: materialize
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error nashs_cage_rvcim_v0_2.tex

paper-clean:
	@if command -v latexmk >/dev/null 2>&1 && [ -f paper/nashs_cage_rvcim_v0_1.tex ]; then \
	  cd paper && latexmk -c nashs_cage_rvcim_v0_1.tex && latexmk -c nashs_cage_rvcim_v0_2.tex && rm -f *.bbl; \
	fi

clean: paper-clean
	rm -rf .tmp
	find simulation -type d -name __pycache__ -prune -exec rm -rf {} +
