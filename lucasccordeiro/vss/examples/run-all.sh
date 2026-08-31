#!/usr/bin/env bash
# Runs every example in this directory with the command line it is meant to be
# run with, and checks the verdict against the one recorded in README.md.
# Requires ESBMC >= 8.5.0 on PATH.
set -u

ESBMC=${ESBMC:-esbmc}
TIMEOUT=${TIMEOUT:-180}
cd "$(dirname "$0")" || exit 1

# timeout(1) is GNU coreutils and is absent from a stock macOS; run unbounded
# rather than failing every check when it is missing.
if command -v timeout >/dev/null 2>&1; then TO=timeout
elif command -v gtimeout >/dev/null 2>&1; then TO=gtimeout
else TO=""; echo "note: no timeout(1) found, running without a time limit" >&2
fi

pass=0
fail=0

check() {
  local expected=$1; shift
  local label out rc verdict
  label=$(printf '%s ' "$@")
  # ESBMC writes its verdict to stderr and only the version banner to stdout.
  out=$(${TO:+$TO "$TIMEOUT"} "$ESBMC" "$@" 2>&1); rc=$?
  verdict=$(printf '%s\n' "$out" | grep -oE 'VERIFICATION (SUCCESSFUL|FAILED|UNKNOWN)' | tail -1)
  if [ "$verdict" = "VERIFICATION $expected" ]; then
    printf '  ok   %-58s %s\n' "$label" "$verdict"
    pass=$((pass + 1))
  else
    [ "$rc" -eq 124 ] && verdict="TIMEOUT after ${TIMEOUT}s"
    printf '  FAIL %-58s got "%s", expected "VERIFICATION %s"\n' "$label" "${verdict:-<none>}" "$expected"
    fail=$((fail + 1))
  fi
}

echo "== ESBMC =="
"$ESBMC" --version

echo "== Bounded model checking =="
check FAILED     assert_example.c
check FAILED     ex1.cpp --unwind 5 --no-unwinding-assertions
check SUCCESSFUL llm_thermostat_example.c
check SUCCESSFUL neural-net.c
check FAILED     neural-net.c --fixedbv
check SUCCESSFUL neural-net.py

echo "== Loops: invariants, k-induction, interval analysis =="
check SUCCESSFUL kinduction.c --k-induction
check SUCCESSFUL kinduction-interval.c --k-induction --interval-analysis
check SUCCESSFUL kinduction-interval2.c --k-induction --interval-analysis
check SUCCESSFUL goto-contractor.c --interval-analysis
check FAILED     incomplete.c --loop-invariant --no-standard-checks
check FAILED     incomplete.py --loop-invariant-check
check SUCCESSFUL crosshair.py --loop-invariant-check
check SUCCESSFUL loop-invariant.py --unwind 101
check FAILED     loop-invariant2.py
check SUCCESSFUL loop-invariant3.py
check SUCCESSFUL while.py --unwind 101
check FAILED     add-overflow.py --overflow-check

echo "== Concurrency =="
check FAILED     interleavings.c --data-races-check
check FAILED     bank-account-bug.c --unwind 2 --no-unwinding-assertions
check SUCCESSFUL bank-account.c --unwind 2 --no-unwinding-assertions
check SUCCESSFUL pthread.c --unwind 11 --context-bound 2
check SUCCESSFUL mutual-exclusion.c --unwind 3 --context-bound 3 --no-unwinding-assertions

echo "== Temporal logic =="
check FAILED     ltl_example.c --ltl ltl_example.ba-2.c -DLTL_PREFIX_BOUND=10

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
