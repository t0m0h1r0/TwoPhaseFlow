# Makefile -- convenience targets for remote experiment execution
SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help push pull setup run run-all ssh cycle plot run-local cycle-local

help:
	@echo "Experiment execution — DEFAULT TARGET: remote server '$$(grep ^REMOTE_HOST remote.conf | cut -d= -f2 | tr -d '\"')'"
	@echo ""
	@echo "Remote (default):"
	@echo "  make run EXP=<path>         Run single experiment on remote"
	@echo "  make run-all CH=<chN>       Run all experiments in chapter on remote"
	@echo "  make cycle EXP=<path>       Push + run + pull (full remote cycle)"
	@echo "  make push / pull            Sync code / results"
	@echo "  make setup                  One-time remote environment setup"
	@echo "  make ssh                    SSH into remote project directory"
	@echo ""
	@echo "Local fallback:"
	@echo "  make run-local EXP=<path>   Run locally (no ssh, no rsync)"
	@echo "  make plot EXP=<path>        Re-plot only from cached .npz"

push:
	./remote.sh push

pull:
	./remote.sh pull

setup:
	./remote.sh setup

run:
	@test -n "$(EXP)" || { echo "Usage: make run EXP=experiment/ch11/exp11_X.py"; exit 1; }
	./remote.sh run $(EXP)

run-all:
	@test -n "$(CH)" || { echo "Usage: make run-all CH=ch11"; exit 1; }
	./remote.sh run-all $(CH)

ssh:
	./remote.sh ssh

cycle:
	@test -n "$(EXP)" || { echo "Usage: make cycle EXP=experiment/ch11/exp11_X.py"; exit 1; }
	./remote.sh push
	./remote.sh run $(EXP)
	./remote.sh pull

plot:
	@test -n "$(EXP)" || { echo "Usage: make plot EXP=experiment/ch11/exp11_X.py"; exit 1; }
	python3 $(EXP) --plot-only

# Local full-run fallback (no ssh, no rsync) — use when iterating without GPU/remote
run-local:
	@test -n "$(EXP)" || { echo "Usage: make run-local EXP=experiment/ch11/exp11_X.py"; exit 1; }
	python3 $(EXP)

# Local cycle shortcut: identical to run-local (kept for symmetry with `cycle`)
cycle-local: run-local
