PYTHON ?= python3
CONFIG ?= simulation/configs/minimal.json
EPISODES ?= 64
SEED ?= 7

.PHONY: help explain verify-release verify-reference-replay verify-feasibility verify-sustained verify-power compile test smoke experiment feasibility sustained power-accounting refresh-reference verify-artifact verify paper paper-clean clean

help:
	@printf '%s\n' \
	  'Nashs Cage / RVCIM commands' \
	  '' \
	  '  make verify           Verify release files, tests, smoke run, and all fixtures' \
	  '  make experiment       Generate a disposable four-arm experiment in .tmp/experiment' \
	  '  make feasibility      Create a new experimental feasibility run in .tmp/feasibility' \
	  '  make sustained        Create a new experimental sustained-response run in .tmp/sustained' \
	  '  make power-accounting Create a new FY2024 fuel-carbon accounting run' \
	  '  make refresh-reference  Maintainer-only refresh of the committed reference fixture' \
	  '  make explain          Print the F0 claim boundary and paper-to-code map' \
	  '  make test             Run the standard-library unit tests' \
	  '  make paper            Build the regenerated manuscript v0.2' \
	  '  make verify-release   Verify committed files against RELEASE_MANIFEST.json' \
	  '  make verify-artifact  Verify the committed reference receipt' \
	  '  make verify-reference-replay  Regenerate and compare deterministic outputs' \
	  '  make verify-feasibility  Verify and replay the experimental feasibility fixture' \
	  '  make verify-sustained  Verify and replay the experimental sustained-response fixture' \
	  '  make verify-power      Replay the frozen fuel-carbon extract and accounting outputs' \
	  '  make clean            Remove local smoke and TeX build products'

explain:
	$(PYTHON) -m simulation explain

verify-release:
	$(PYTHON) tools/verify_release.py --root . --manifest RELEASE_MANIFEST.json

verify-reference-replay:
	$(PYTHON) tools/verify_reference_replay.py --root . --reference-dir artifacts/reference_run

verify-feasibility:
	$(PYTHON) tools/run_feasibility.py verify --out artifacts/feasibility_v03 --replay

verify-sustained:
	$(PYTHON) tools/run_sustained.py verify --out artifacts/sustained_v04 --replay

verify-power:
	$(PYTHON) tools/run_power_accounting.py verify --out artifacts/power_jp_fy2024 --replay

compile:
	$(PYTHON) -m py_compile simulation/__init__.py simulation/__main__.py simulation/rvcim_sim.py simulation/feasibility.py simulation/sustained.py
	$(PYTHON) -m py_compile tools/verify_release.py tools/verify_reference_replay.py tools/run_feasibility.py tools/run_sustained.py tools/run_power_accounting.py
	$(PYTHON) -m py_compile simulation/tests/test_rvcim_sim.py simulation/tests/test_feasibility.py simulation/tests/test_sustained.py tools/tests/test_verify_release.py tools/tests/test_feasibility_runner.py tools/tests/test_sustained_runner.py tools/tests/test_power_accounting.py

test:
	$(PYTHON) -m unittest -v simulation.tests.test_rvcim_sim
	$(PYTHON) -m unittest -v simulation.tests.test_feasibility
	$(PYTHON) -m unittest -v simulation.tests.test_sustained
	$(PYTHON) -m unittest -v tools.tests.test_verify_release
	$(PYTHON) -m unittest -v tools.tests.test_feasibility_runner
	$(PYTHON) -m unittest -v tools.tests.test_sustained_runner
	$(PYTHON) -m unittest -v tools.tests.test_power_accounting

smoke:
	$(PYTHON) -m simulation smoke --config "$(CONFIG)" --episodes 4 --seed 101 --out .tmp/smoke
	$(PYTHON) -m simulation verify --receipt .tmp/smoke/receipt.json

experiment:
	$(PYTHON) -m simulation run --config "$(CONFIG)" --episodes "$(EPISODES)" --seed "$(SEED)" --out .tmp/experiment --overwrite
	$(PYTHON) -m simulation verify --receipt .tmp/experiment/receipt.json

feasibility:
	$(PYTHON) tools/run_feasibility.py run --out .tmp/feasibility

sustained:
	$(PYTHON) tools/run_sustained.py run --out .tmp/sustained

power-accounting:
	$(PYTHON) tools/run_power_accounting.py run --out .tmp/power-accounting

refresh-reference:
	@printf '%s\n' 'Maintainer operation: refreshing the committed 64-episode fixture.'
	$(PYTHON) -m simulation run --config simulation/configs/minimal.json --episodes 64 --seed 7 --out artifacts/reference_run --overwrite
	$(PYTHON) -m simulation verify --receipt artifacts/reference_run/receipt.json

verify-artifact:
	$(PYTHON) -m simulation verify --receipt artifacts/reference_run/receipt.json

verify: verify-release compile test smoke verify-artifact verify-reference-replay verify-feasibility verify-sustained verify-power

paper:
	mkdir -p .tmp/paper
	cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=../.tmp/paper nashs_cage_rvcim_v0_2.tex

paper-clean:
	rm -rf .tmp/paper

clean: paper-clean
	rm -rf .tmp
	find simulation -type d -name __pycache__ -prune -exec rm -rf {} +
