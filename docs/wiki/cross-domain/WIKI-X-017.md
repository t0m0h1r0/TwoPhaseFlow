# WIKI-X-017: §13 Production Config Pattern — Research-to-Paper Transition

## Context

After completing the research phase (47 diagnostic/sweep configs in `experiment/ch13/config/`), the repository is cleaned to a production state for paper submission. This documents the naming convention, config design decisions, and runner invocation.

## Clean-Slate Transition

When moving from research to paper-ready:
```bash
# Delete all research/diagnostic artifacts
rm -rf experiment/ch13/config/
rm -rf experiment/ch13/results/
mkdir -p experiment/ch13/config

# Commit
git commit -m "chore(ch13): remove all research configs and stale results — clean slate"
```

`experiment/ch13/run.py` is **retained** (the unified runner is production code).

## Naming Convention

Config files are named `ch13_0N_<description>.yaml`, directly tied to paper section §13.N:

| File | Paper section | Physics regime |
|---|---|---|
| `ch13_01_capwave_waterair.yaml` | §13.1 Capillary wave | ρ=833:1, GFM, α=1.5 |
| `ch13_02_rising_bubble.yaml` | §13.2 Rising bubble | ρ=10:1, bulk PPE, α=1 |
| `ch13_03_taylor_deformation.yaml` | §13.3 Taylor deformation | ρ=1:1, Couette, α=2, sweep |

## Config Design Decisions

### Grid strategy (α)
| Benchmark | α | Reason |
|---|---|---|
| Capillary wave | 1.5 | High-ρ (833:1) requires GFM; local refinement reduces parasitic currents |
| Rising bubble | 1.0 | Moderate-ρ (10:1); α=2 caused KE spike 3910× at step 2 (WIKI-E-022) |
| Taylor deformation | 2.0 | Interface refinement for thin-neck deformation at high Ca |

### Volume conservation
- **Capillary wave**: `phi_primary_transport: true` → machine-precision (7.55e-15)
- **Rising bubble**: default (no phi_primary_transport) → acceptable 3.09e-5

### Reinit
- **Capillary/bubble**: `reinit_method: eikonal_xi`, `reinit_every: 2`, `reinit_eps_scale: 1.0/1.4`
- **Taylor**: not specified (defaults to code default; steady-state deformation regime differs)

## Runner Invocation

```bash
# Correct: pass script path + config name as separate tokens
make cycle EXP="experiment/ch13/run.py ch13_01_capwave_waterair"
make run   EXP="experiment/ch13/run.py ch13_02_rising_bubble"
make plot  EXP="experiment/ch13/run.py ch13_01_capwave_waterair"

# WRONG: passing YAML path directly → python3 tries to exec YAML → SyntaxError
make run EXP=experiment/ch13/config/ch13_01_capwave_waterair.yaml  # BAD
```

The Makefile does `./remote.sh run $(EXP)` → `cmd_run script extra_args` → `python3 "$script" $extra_args`. So the first token of EXP must be a `.py` file.

## Worktree Recovery

If a worktree directory is accidentally deleted, the branch commits survive:
```bash
git worktree prune                             # remove stale registration
git worktree add <path> <branch-name>          # recreate at same or new path
```

The branch head (all commits) is fully intact in the main repo's `.git/`.

## sources

- `experiment/ch13/run.py`
- `experiment/ch13/config/ch13_01_capwave_waterair.yaml`
- `remote.sh` (cmd_run function)
- Makefile (run/cycle/plot targets)

## depends_on

- `[[WIKI-L-021]]` (matplotlib CJK font issue)
- `[[WIKI-E-022]]` (KE spike at α=2 for rising bubble)
- `[[WIKI-X-016]]` (reinit ε-scale dispatch policy)
