# Execution Environment Notes

Date: 2026-04-15

This repository is often used from sibling git worktrees. The local virtual
environment is kept only in the top checkout:

```sh
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python
```

From a sibling worktree such as
`/Users/tomohiro/Downloads/TwoPhaseFlow-researcharchitect-ch12`, use:

```sh
../TwoPhaseFlow/.venv/bin/python
```

Do not infer failure from `/usr/bin/python` or `python3` lacking NumPy; the
project environment is the top-checkout `.venv`.

Expensive experiment re-runs should use the external Python server through
`remote.sh`:

```sh
./remote.sh check
./remote.sh push
./remote.sh run experiment/ch12/exp12_XX_name.py
./remote.sh pull
```

`remote.conf` currently points to host `python` and remote directory
`/root/TwoPhaseFlow`.
