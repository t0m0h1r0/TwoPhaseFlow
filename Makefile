# Makefile -- convenience targets for experiment execution
# Auto-detects remote server availability; falls back to local when unreachable.
SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help check push pull setup run run-all ssh cycle plot run-local cycle-local test test-local

help:
	@echo "Experiment execution — remote server '$$(grep ^REMOTE_HOST remote.conf | cut -d= -f2 | tr -d '\"')'"
	@echo "  run / cycle / test auto-detect remote; fall back to local."
	@echo ""
	@echo "Auto-detect (remote → local fallback):"
	@echo "  make run EXP=<path>         Run single experiment"
	@echo "  make cycle EXP=<path>       Push + run + pull (or local fallback)"
	@echo "  make test                   pytest (remote+GPU or local+CPU)"
	@echo ""
	@echo "Always remote:"
	@echo "  make run-all CH=<chN>       Run all experiments in chapter on remote"
	@echo "  make push / pull            Sync code / results"
	@echo "  make setup                  One-time remote environment setup"
	@echo "  make ssh                    SSH into remote project directory"
	@echo "  make check                  Test remote SSH reachability"
	@echo ""
	@echo "Always local:"
	@echo "  make run-local EXP=<path>   Run locally (no ssh, no rsync)"
	@echo "  make test-local             pytest locally (CPU only)"
	@echo "  make plot EXP=<path>        Re-plot only from cached .npz"
	@echo ""
	@echo "Variables:"
	@echo "  EXP=<path>                  Experiment script path"
	@echo "  CH=<chN>                    Chapter name (ch12, ch13, ...)"
	@echo "  PYTEST_ARGS=<args>          Extra pytest arguments"
	@echo "  TWOPHASE_FORCE_LOCAL=1      Skip remote check, always run locally"

check:
	./remote.sh check

push:
	./remote.sh push

pull:
	./remote.sh pull

setup:
	./remote.sh setup

run:
	@test -n "$(EXP)" || { echo "Usage: make run EXP=experiment/run.py ARGS='--config <stem>'"; exit 1; }
	@if ./remote.sh check >/dev/null 2>&1; then \
		./remote.sh run $(EXP) $(ARGS); \
	else \
		echo "INFO: Remote unavailable, running locally (CPU)."; \
		python3 $(EXP) $(ARGS); \
	fi

run-all:
	@test -n "$(CH)" || { echo "Usage: make run-all CH=ch12"; exit 1; }
	./remote.sh run-all $(CH)

ssh:
	./remote.sh ssh

cycle:
	@test -n "$(EXP)" || { echo "Usage: make cycle EXP=experiment/run.py ARGS='--config <stem>'"; exit 1; }
	@if ./remote.sh check >/dev/null 2>&1; then \
		./remote.sh push && ./remote.sh run $(EXP) $(ARGS) && ./remote.sh pull; \
	else \
		echo "INFO: Remote unavailable, running locally (CPU)."; \
		python3 $(EXP) $(ARGS); \
	fi

test:
	@if ./remote.sh check >/dev/null 2>&1; then \
		./remote.sh push && ./remote.sh test $(PYTEST_ARGS); \
	else \
		echo "INFO: Remote unavailable, running tests locally (CPU only)."; \
		cd src && python -m pytest twophase/tests -v --tb=short $(PYTEST_ARGS); \
	fi

plot:
	@test -n "$(EXP)" || { echo "Usage: make plot EXP=experiment/run.py ARGS='--config <stem>'"; exit 1; }
	python3 $(EXP) --plot-only $(ARGS)

# ── Always-local targets ──────────────────────────────────────────────────
run-local:
	@test -n "$(EXP)" || { echo "Usage: make run-local EXP=experiment/run.py ARGS='--config <stem>'"; exit 1; }
	python3 $(EXP) $(ARGS)

test-local:
	cd src && python -m pytest twophase/tests -v --tb=short $(PYTEST_ARGS)

cycle-local: run-local
