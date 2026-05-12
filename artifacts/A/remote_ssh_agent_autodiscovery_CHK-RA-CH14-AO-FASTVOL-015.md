# CHK-RA-CH14-AO-FASTVOL-015 - remote ssh-agent autodiscovery

## Problem

Codex desktop sessions often start with `SSH_AUTH_SOCK` unset even when the
usable ssh-agent socket still exists.  `make run`, `make cycle`, and `make test`
therefore entered the local fallback path before the remote GPU could be used.

## Change

`remote.sh` now resolves a usable ssh-agent socket before dispatching any remote
operation:

1. keep the inherited `SSH_AUTH_SOCK` when it is a live agent socket,
2. accept `TWOPHASE_SSH_AUTH_SOCK=/path/to/socket` as an explicit override,
3. try stable project candidates from `remote.conf`,
4. try common macOS/Linux agent socket globs,
5. preserve `TWOPHASE_FORCE_LOCAL=1` as an explicit fail-closed local override.

The stable candidates are:

```text
/private/tmp/codex-ssh-agent-test.sock
/tmp/codex-ssh-agent-test.sock
```

## Validation

```text
bash -n remote.sh
env -u SSH_AUTH_SOCK ./remote.sh check
env -u SSH_AUTH_SOCK make check
TWOPHASE_FORCE_LOCAL=1 ./remote.sh check
git diff --check
```

Result:

```text
bash syntax PASS,
remote check PASS with SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock,
make check PASS against remote python,
TWOPHASE_FORCE_LOCAL still fails closed,
diff check PASS.
```

## Policy Notes

```text
[SOLID-S] ssh-agent discovery is isolated in the remote execution wrapper.
[SOLID-X] no solver source, numerical operator, experiment result, main merge,
fallback numerical method, dense AO runtime fallback, implicit PCG fallback, or
hidden GPU D2H control path changed.
```
