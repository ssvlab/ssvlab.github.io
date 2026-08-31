# Examples

Every command below was run against **ESBMC 8.5.0** and the recorded verdict is
the one the tool actually produces. `./run-all.sh` re-checks the whole table;
it exits non-zero if any verdict has drifted.

```bash
./run-all.sh            # uses `esbmc` from PATH
ESBMC=/path/to/esbmc ./run-all.sh
```

## Bounded model checking

| Example | Command | Verdict | Point of the example |
| --- | --- | --- | --- |
| `assert_example.c` | `esbmc assert_example.c` | FAILED | The smallest possible counterexample: `__ESBMC_assert` with a message. |
| `ex1.cpp` | `esbmc ex1.cpp --unwind 5 --no-unwinding-assertions` | FAILED | Two defects on one line: `malloc` is never checked for NULL (reported first) and `i <= n` writes one past the buffer. Add `--multi-property` to see both. |
| `llm_thermostat_example.c` | `esbmc llm_thermostat_example.c` | SUCCESSFUL | A green verdict that means nothing: the temperature is a constant, so the guard is dead and the assertion is unreachable. ESBMC even reports `0 remaining after simplification`. |
| `neural-net.c` | `esbmc neural-net.c` | SUCCESSFUL | A two-node ReLU network under the default IEEE-754 model. |
| `neural-net.c` | `esbmc neural-net.c --fixedbv` | FAILED | The same assertion under fixed-point. There is no margin to lose: under IEEE-754 the sum rounds to *exactly* the threshold double (`2.74500000000000010658`) and the assertion holds by equality, so any other rounding breaks it. The number model is part of the specification. |
| `neural-net.py` | `esbmc neural-net.py` | SUCCESSFUL | The same network in Python. |

## Loops: unwinding, invariants, k-induction, interval analysis

| Example | Command | Verdict | Point of the example |
| --- | --- | --- | --- |
| `kinduction.c` | `esbmc kinduction.c --k-induction` | SUCCESSFUL | An infinite loop whose invariant k-induction finds at `k = 2`. |
| `kinduction-interval.c` | `esbmc kinduction-interval.c --k-induction --interval-analysis` | SUCCESSFUL | k-induction alone returns UNKNOWN; the interval domain supplies the missing range fact. |
| `kinduction-interval2.c` | `esbmc kinduction-interval2.c --k-induction --interval-analysis` | SUCCESSFUL | Same, on a loop with a nondeterministic start value. |
| `goto-contractor.c` | `esbmc goto-contractor.c --interval-analysis` | SUCCESSFUL | A loop bounded by a nondeterministic exit condition; the interval domain proves `x >= y` without unwinding to the 1000-iteration limit. Substitute `--goto-contractor` for the IBEX contractor, which needs a build configured with `-DENABLE_GOTO_CONTRACTOR=ON`. |
| `incomplete.c` | `esbmc incomplete.c --loop-invariant --no-standard-checks` | FAILED | The invariants are deliberately too weak — the inductive step fails. Strengthening them is Exercise 3; it needs an exact invariant for `j` and bounds on `n` and `k`, because `j = j + i` overflows otherwise. |
| `incomplete.py` | `esbmc incomplete.py --loop-invariant-check` | FAILED | The same weak invariants in Python. |
| `crosshair.py` | `esbmc crosshair.py --loop-invariant-check` | SUCCESSFUL | What a *sufficient* invariant looks like: bounds plus the relational equalities. |
| `loop-invariant.py` | `esbmc loop-invariant.py --unwind 101` | SUCCESSFUL | Brute force: 100 iterations unwound in full. |
| `loop-invariant2.py` | `esbmc loop-invariant2.py` | FAILED | The loop replaced by one iteration — unsound abstraction. |
| `loop-invariant3.py` | `esbmc loop-invariant3.py` | SUCCESSFUL | The loop replaced by its invariant, discharged without unwinding. |
| `while.py` | `esbmc while.py --unwind 101` | SUCCESSFUL | No assertion, so no VCC: ESBMC checks properties, not programs. |
| `add-overflow.py` | `esbmc add-overflow.py --overflow-check` | FAILED | `numpy.int32` wraps silently; without `--overflow-check` there is nothing to violate. |

`overflow.py` and `add-overflow.py` are byte-identical; both names are kept so
older slide decks that refer to either one still resolve. `thermostat.c` is an
older variant of `llm_thermostat_example.c` and is not part of the table above.

## Concurrency

| Example | Command | Verdict | Point of the example |
| --- | --- | --- | --- |
| `interleavings.c` | `esbmc interleavings.c --data-races-check` | FAILED | Unsynchronised `x++` / `x--`: a data race, reported without needing an assertion. |
| `bank-account-bug.c` | `esbmc bank-account-bug.c --unwind 2 --no-unwinding-assertions` | FAILED | Check-then-act on a shared balance; the counterexample overdraws the account to -400. |
| `bank-account.c` | `esbmc bank-account.c --unwind 2 --no-unwinding-assertions` | SUCCESSFUL | The same code with the check and the update inside one mutex. |
| `pthread.c` | `esbmc pthread.c --unwind 11 --context-bound 2` | SUCCESSFUL | Two threads incrementing 10 times each under a lock: `n == 20`. |
| `mutual-exclusion.c` | `esbmc mutual-exclusion.c --unwind 3 --context-bound 3 --no-unwinding-assertions` | SUCCESSFUL | Peterson's algorithm: at most one thread in the critical section. |

## Temporal logic

The Büchi monitor is generated from the **positive** LTL formula; ESBMC negates
it internally. Regenerate it with the ESBMC fork of `ltl2ba`
([libltl2ba](https://github.com/esbmc/libltl2ba)) — the upstream Homebrew
`ltl2ba` has no `-O c` backend, and monitors from libltl2ba v2.1 or older are
missing the `__ESBMC_switch_from_monitor()` call
([esbmc/esbmc#6546](https://github.com/esbmc/esbmc/issues/6546)), which makes
ESBMC 8.5 report `VERIFICATION UNKNOWN`.

```bash
ltl2ba -O c -H '"vars.h"' -f 'G({pressed} -> F {charge > min})' > ltl_example.ba-2.c
esbmc ltl_example.c --ltl ltl_example.ba-2.c -DLTL_PREFIX_BOUND=10
```

Verdict: FAILED, with `Final lowest outcome: LTL_FAILING`. `LTL_PREFIX_BOUND`
caps the length of the monitored prefix; the loop in `ltl_example.c` must run
long enough for the monitor to reach a decisive state, which is why it iterates
twice.

## Two flags worth knowing in 8.5

- ESBMC stops at the first violated property. Add `--multi-property` for a
  verdict on every property in one run.
- The default solver is now **Bitwuzla**. Use `--z3`, `--cvc5` or `--boolector`
  to compare, and treat agreement between two solvers as the bar for a claim.
