#!/usr/bin/env bash
# Checks every verdict quoted in exercises.pdf. Requires ESBMC >= 8.5.0; the
# LTL monitors are committed, so libltl2ba is only needed to regenerate them.
set -u

ESBMC=${ESBMC:-esbmc}
TIMEOUT=${TIMEOUT:-180}
cd "$(dirname "$0")" || exit 1

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
    printf '  ok   %-62s %s\n' "$label" "$verdict"
    pass=$((pass + 1))
  else
    [ "$rc" -eq 124 ] && verdict="TIMEOUT after ${TIMEOUT}s"
    printf '  FAIL %-62s got "%s", expected "VERIFICATION %s"\n' "$label" "${verdict:-<none>}" "$expected"
    fail=$((fail + 1))
  fi
}

echo "== ESBMC =="
"$ESBMC" --version

echo "== Exercise 1: bounded model checking =="
check SUCCESSFUL ramp.c
check FAILED     settle.py --unwind 8

echo "== Exercise 2: mutual exclusion on the display bus =="
check SUCCESSFUL bus.c --ltl bus-mutex-neg.ba-2.c -DLTL_PREFIX_BOUND=10 --context-bound 3
check FAILED     bus-bad.c --ltl bus-mutex-neg.ba-2.c -DLTL_PREFIX_BOUND=10 --context-bound 3

echo "== Exercise 3: plant control properties =="
check SUCCESSFUL plant.c --ltl valve-neg.ba-2.c -DLTL_PREFIX_BOUND=10
check FAILED     plant.c --ltl heater-neg.ba-2.c -DLTL_PREFIX_BOUND=10
check FAILED     plant.c --ltl screen-neg.ba-2.c -DLTL_PREFIX_BOUND=10
check SUCCESSFUL solutions/plant-fixed.c --ltl heater-neg.ba-2.c -DLTL_PREFIX_BOUND=10

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
