#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/remote.conf"

usage() {
    cat <<'USAGE'
Usage: ./remote.sh <command> [args]

Commands:
  check                 Test SSH reachability of remote (exit 0 = OK)
  push                  Sync codebase to remote (excludes results)
  pull                  Sync results back from remote
  setup                 One-time: install Python, venv, dependencies on remote
  run <script.py>       Run a single experiment on remote
  run-all <ch11|ch12>   Run all experiments in a chapter
  test [pytest-args]    Run pytest on remote (default: --gpu)
  ssh                   Open an interactive SSH session to remote project dir

Examples:
  ./remote.sh check
  ./remote.sh push
  ./remote.sh setup
  ./remote.sh run experiment/ch11/exp11_01_ccd_convergence.py
  ./remote.sh run-all ch11
  ./remote.sh test
  ./remote.sh test -k test_ccd --gpu
  ./remote.sh pull

Environment:
  TWOPHASE_FORCE_LOCAL=1   Skip remote check, always fail cmd_check
USAGE
    exit 1
}

# ── Push codebase to remote (excludes results/) ──────────────────────────────
# Uses --checksum so a parallel worktree can't silently win a mtime+size
# tie. (CHK-120: race between worktrees pushing the same paths produced
# stale remote code that invalidated Round 2-5 GPU measurements.)
cmd_push() {
    echo "==> Pushing codebase to ${REMOTE_HOST}:${REMOTE_DIR}"
    rsync -avz --delete --checksum \
        "${RSYNC_EXCLUDE[@]}" \
        --exclude='experiment/*/results/' \
        "$SCRIPT_DIR/" \
        "${REMOTE_HOST}:${REMOTE_DIR}/"
    echo "==> Push complete."
}

# ── Pull results back from remote ────────────────────────────────────────────
cmd_pull() {
    echo "==> Pulling results from ${REMOTE_HOST}:${REMOTE_DIR}"
    for ch_dir in "$SCRIPT_DIR"/experiment/ch*/; do
        local ch
        ch="$(basename "$ch_dir")"
        local remote_path="${REMOTE_DIR}/experiment/${ch}/results/"
        local local_path="${SCRIPT_DIR}/experiment/${ch}/results/"
        # Skip if remote results dir does not exist
        if ssh "${REMOTE_HOST}" "test -d '${remote_path}'" 2>/dev/null; then
            echo "    ${ch}/results/ ..."
            mkdir -p "$local_path"
            rsync -avz \
                "${REMOTE_HOST}:${remote_path}" \
                "${local_path}"
        fi
    done
    echo "==> Pull complete."
}

# ── One-time remote setup ────────────────────────────────────────────────────
cmd_setup() {
    # Install rsync on remote first (needed for push)
    echo "==> Installing rsync on ${REMOTE_HOST}"
    ssh "${REMOTE_HOST}" "apt-get update -qq && apt-get install -y -qq rsync >/dev/null 2>&1"
    # Push code so the remote has src/ to install
    cmd_push
    echo "==> Setting up Python environment on ${REMOTE_HOST}"
    ssh "${REMOTE_HOST}" bash -s <<SETUP
set -euo pipefail

# System packages
echo "--- Installing system packages ---"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-dev python3-pip >/dev/null

# Create venv if it doesn't exist
if [ ! -d "${VENV_DIR}" ]; then
    echo "--- Creating venv at ${VENV_DIR} ---"
    ${PYTHON} -m venv "${VENV_DIR}"
fi

# Activate and install
echo "--- Installing twophase package (editable) ---"
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel -q
pip install -e "${REMOTE_DIR}/src[gpu]" -q
pip install matplotlib h5py pyyaml -q

echo "--- Verifying installation ---"
python -c "import twophase; print('twophase OK')"
python -c "import numpy; print(f'numpy {numpy.__version__}')"
python -c "import scipy; print(f'scipy {scipy.__version__}')"
python -c "import matplotlib; print(f'matplotlib {matplotlib.__version__}')"

echo "--- Setup complete ---"
SETUP
}

# ── Run a single experiment ──────────────────────────────────────────────────
cmd_run() {
    local script="${1:?Error: provide a script path, e.g. experiment/ch11/exp11_01_ccd_convergence.py}"

    if [ ! -f "${SCRIPT_DIR}/${script}" ]; then
        echo "Error: ${script} not found locally. Check the path."
        exit 1
    fi

    echo "==> Running ${script} on ${REMOTE_HOST}"
    ssh "${REMOTE_HOST}" bash -s <<RUN
set -euo pipefail
source "${VENV_DIR}/bin/activate"
export TWOPHASE_USE_GPU=1
cd "${REMOTE_DIR}"
echo "--- Starting: ${script} ---"
time ${PYTHON} "${script}"
echo "--- Finished: ${script} ---"
RUN
}

# ── Run all experiments in a chapter ─────────────────────────────────────────
cmd_run_all() {
    local chapter="${1:?Error: provide chapter name, e.g. ch11 or ch12}"

    echo "==> Running all experiments in ${chapter} on ${REMOTE_HOST}"
    ssh "${REMOTE_HOST}" bash -s <<RUNALL
set -euo pipefail
source "${VENV_DIR}/bin/activate"
export TWOPHASE_USE_GPU=1
cd "${REMOTE_DIR}"

failed=0
for script in experiment/${chapter}/exp*.py; do
    echo ""
    echo "====== \$(basename \$script) ======"
    if time ${PYTHON} "\$script"; then
        echo "  -> OK"
    else
        echo "  -> FAILED (exit \$?)"
        failed=\$((failed + 1))
    fi
done

if [ \$failed -gt 0 ]; then
    echo ""
    echo "WARNING: \$failed experiment(s) failed."
    exit 1
fi
echo ""
echo "All experiments in ${chapter} completed successfully."
RUNALL
}

# ── Remote availability check ────────────────────────────────────────────────
is_remote_available() {
    if [ "${TWOPHASE_FORCE_LOCAL:-0}" = "1" ]; then
        return 1
    fi
    ssh -o ConnectTimeout="${SSH_TIMEOUT:-5}" -o BatchMode=yes \
        "${REMOTE_HOST}" true 2>/dev/null
}

cmd_check() {
    if is_remote_available; then
        echo "Remote '${REMOTE_HOST}' is reachable."
        return 0
    else
        echo "Remote '${REMOTE_HOST}' is NOT reachable."
        return 1
    fi
}

# ── Run pytest on remote ────────────────────────────────────────────────────
cmd_test() {
    local extra_args="${*:---gpu}"

    echo "==> Running pytest on ${REMOTE_HOST} with args: ${extra_args}"
    ssh "${REMOTE_HOST}" bash -s -- ${extra_args} <<'TEST'
set -euo pipefail
source /root/TwoPhaseFlow/.venv/bin/activate
export TWOPHASE_USE_GPU=1
cd /root/TwoPhaseFlow/src
echo "--- pytest $* ---"
python -m pytest twophase/tests "$@" -v --tb=short
echo "--- pytest finished ---"
TEST
}

# ── Interactive SSH ──────────────────────────────────────────────────────────
cmd_ssh() {
    echo "==> Opening SSH session to ${REMOTE_HOST}:${REMOTE_DIR}"
    ssh -t "${REMOTE_HOST}" "cd ${REMOTE_DIR} && source ${VENV_DIR}/bin/activate && exec bash"
}

# ── Dispatch ─────────────────────────────────────────────────────────────────
case "${1:-}" in
    check)    cmd_check ;;
    push)     cmd_push ;;
    pull)     cmd_pull ;;
    setup)    cmd_setup ;;
    run)      shift; cmd_run "$@" ;;
    run-all)  shift; cmd_run_all "$@" ;;
    test)     shift; cmd_test "$@" ;;
    ssh)      cmd_ssh ;;
    *)        usage ;;
esac
