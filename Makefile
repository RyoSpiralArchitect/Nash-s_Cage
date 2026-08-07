PYTHON ?= python3
CONFIG ?= simulation/configs/minimal.json
REFERENCE_DIR ?= artifacts/reference_run
SMOKE_DIR ?= .tmp/smoke
EPISODES ?= 64
SEED ?= 7

.PHONY: help explain verify-release verify-reference-replay compile test smoke experiment verify-artifact verify paper paper-clean clean

help:
	@printf '%s\n' \
	  'Nashs Cage / RVCIM commands' \
	  '' \
	  '  make verify           Verify release files, tests, smoke run, and reference receipt' \
	  '  make experiment       Generate the complete four-arm reference experiment' \
	  '  make explain          Print the F0 claim boundary and paper-to-code map' \
	  '  make test             Run the standard-library unit tests' \
	  '  make paper            Build the regenerated manuscript v0.2' \
	  '  make verify-release   Verify committed files against RELEASE_MANIFEST.json' \
	  '  make verify-artifact  Verify the committed reference receipt' \
	  '  make verify-reference-replay  Regenerate and compare deterministic outputs' \
	  '  make clean            Remove local smoke and TeX build products'

explain:
	$(PYTHON) -m simulation explain

verify-release:
	$(PYTHON) tools/verify_release.py --root . --manifest RELEASE_MANIFEST.json

verify-reference-replay:
	$(PYTHON) tools/verify_reference_replay.py --root . --reference-dir $(REFERENCE_DIR)

compile:
	$(PYTHON) -m py_compile simulation/__init__.py simulation/__main__.py simulation/rvcim_sim.py
	$(PYTHON) -m py_compile tools/verify_release.py tools/verify_reference_replay.py

test:
	$(PYTHON) -m unittest discover -s simulation/tests -v
	$(PYTHON) -m unittest discover -s tools/tests -v

smoke:
	$(PYTHON) -m simulation smoke --config $(CONFIG) --episodes 4 --seed 101 --out $(SMOKE_DIR)
	$(PYTHON) -m simulation verify --receipt $(SMOKE_DIR)/receipt.json

experiment:
	$(PYTHON) -m simulation run --config $(CONFIG) --episodes $(EPISODES) --seed $(SEED) --out $(REFERENCE_DIR) --overwrite
	$(PYTHON) -m simulation verify --receipt $(REFERENCE_DIR)/receipt.json

verify-artifact:
	$(PYTHON) -m simulation verify --receipt "$(REFERENCE_DIR)/receipt.json"

verify: verify-release compile test smoke verify-artifact verify-reference-replay

paper:
	mkdir -p .tmp/paper
	cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=../.tmp/paper nashs_cage_rvcim_v0_2.tex

paper-clean:
	rm -rf .tmp/paper

clean: paper-clean
	rm -rf .tmp
	find simulation -type d -name __pycache__ -prune -exec rm -rf {} +
