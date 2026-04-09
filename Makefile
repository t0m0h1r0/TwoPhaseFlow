# Makefile -- convenience targets for remote experiment execution
SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help push pull setup run run-all ssh cycle plot

help:
	@echo "Remote experiment targets:"
	@echo "  make push              Sync codebase to remote"
	@echo "  make pull              Sync results from remote"
	@echo "  make setup             One-time remote environment setup"
	@echo "  make run EXP=<path>    Run single experiment on remote"
	@echo "  make run-all CH=<chN>  Run all experiments in chapter"
	@echo "  make cycle EXP=<path>  Push + run + pull (full cycle)"
	@echo "  make plot EXP=<path>   Local re-plot with --plot-only"
	@echo "  make ssh               SSH into remote project directory"

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
