PYTHON ?= python3
CONFIG ?= simulation/configs/minimal.json
REFERENCE_DIR ?= artifacts/reference_run
SMOKE_DIR ?= .tmp/smoke
EPISODES ?= 64
SEED ?= 7

.PHONY: help explain compile test smoke experiment verify-artifact verify paper paper-clean clean

help:
	@printf '%s\n' \
	  'Nashs Cage / RVCIM commands' \
	  '' \
	  '  make explain          Print the F0 claim boundary and paper-to-code map' \
	  '  make compile          Compile-check the Python sources' \
	  '  make test             Run the standard-library unit tests' \
	  '  make smoke            Run and verify a fast four-arm experiment' \
	  '  make experiment       Regenerate the committed reference experiment' \
	  '  make verify-artifact  Verify the committed SHA-256 receipt' \
	  '  make verify           Run compile, tests, smoke, and receipt checks' \
	  '  make paper            Build manuscript v0.2 with latexmk and Biber' \
	  '  make clean            Remove local smoke and TeX build products'

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
	$(PYTHON) -m simulation verify --receipt $(REFERENCE_DIR)/receipt.json

verify: compile test smoke verify-artifact

paper:
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error nashs_cage_rvcim_v0_2.tex

paper-clean:
	cd paper && latexmk -c nashs_cage_rvcim_v0_1.tex && latexmk -c nashs_cage_rvcim_v0_2.tex && rm -f *.bbl

clean: paper-clean
	rm -rf .tmp
	find simulation -type d -name __pycache__ -prune -exec rm -rf {} +
