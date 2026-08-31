# LLM-generated code

Three implementations of the chemical-process controller from the exercise list,
all produced by a language model from the same natural-language specification.
All three look plausible; they are not equally correct.

| File | Synchronisation |
| --- | --- |
| `embedded_system_llm.c` | none |
| `embedded_system_unsafe1.c` | one global mutex, taken again inside `set_heater`/`set_valve_position` while already held |
| `embedded_system_unsafe2.c` | one mutex per shared variable |

## Commands and verdicts (ESBMC 8.5.0)

The worker threads are `while (1)` loops, so every run is bounded and every
verdict below is a statement about the bounded model, not about the program.

| Command | Verdict | Runtime |
| --- | --- | --- |
| `esbmc embedded_system_llm.c --data-races-check --context-bound 2 --unwind 2 --no-unwinding-assertions` | FAILED — W/W data race on `valve_position` | ~2 min |
| `esbmc embedded_system_unsafe2.c --data-races-check --context-bound 2 --unwind 2 --no-unwinding-assertions` | FAILED — the heater assertion in `display_process` | ~1 min |
| `esbmc embedded_system_unsafe1.c --data-races-check --context-bound 1 --unwind 2 --no-unwinding-assertions` | SUCCESSFUL | ~7 s |
| `esbmc embedded_system_unsafe1.c --data-races-check --context-bound 2 --unwind 2 --no-unwinding-assertions` | did not finish in 400 s | — |

`unsafe1.c` is the interesting one. The global mutex does remove the races the
first file has, so at small bounds ESBMC returns SUCCESSFUL — but the code takes
that same non-recursive mutex twice on the path
`temperature_process` → `set_heater`, which self-deadlocks on real POSIX.
`--deadlock-check` at `--context-bound 1 --unwind 2` still reports SUCCESSFUL,
because the worker loops never terminate and so the join is never reached within
the bound. Getting ESBMC to report that defect is Exercise 14(b) in the exercise
list.

Raising `--context-bound` past 2 on these files is expensive: the interleaving
space grows quickly with four threads. Raise it one step at a time.
