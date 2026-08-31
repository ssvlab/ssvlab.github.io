# ECPS sources for the exercises

These back `../exercises.pdf`. `./run-all.sh` checks every verdict quoted there
and exits non-zero if any has drifted; all were measured against ESBMC 8.5.0.

| File | Used by | Verdict |
| --- | --- | --- |
| `ramp.c` | Ex. 1 — actuator duty ramp, the BMC worked example | SUCCESSFUL |
| `settle.py` | Ex. 1(e) — control loop that does not terminate for an odd setpoint | FAILED (unwinding assertion) |
| `bus.c` | Ex. 2 — display bus arbitrated by Peterson | SUCCESSFUL, `LTL_SUCCEEDING` |
| `bus-bad.c` | Ex. 2(d) — same, with `turn = 1` deleted | FAILED, `LTL_BAD` |
| `plant.c` | Ex. 3 — the Figure 1 controller as a cyclic executive | see below |
| `solutions/plant-fixed.c` | Ex. 3(d) reference solution — **spoiler** | SUCCESSFUL |

## The three plant properties

| Property | Monitor | Verdict |
| --- | --- | --- |
| `!G({pressure > 500} -> F {valve_open})` | `valve-neg.ba-2.c` | SUCCESSFUL, `LTL_SUCCEEDING` |
| `!G({temperature < 20} -> F {heater_on})` | `heater-neg.ba-2.c` | FAILED, `LTL_FAILING` |
| `!G({fresh_sample} -> F {displayed})` | `screen-neg.ba-2.c` | FAILED, `LTL_FAILING` |

The heater and valve properties have the same shape but different outcomes, and
that is the point of Exercise 3(c). `temperature` lives in BSS, so it reads
0 °C at power-on — which satisfies "below 20 °C" before the controller has taken
a single sample, while the heater is still off. `pressure` reads 0 bar, which
does *not* satisfy "above 500 bar", so the pressure loop has no such obligation.
`solutions/plant-fixed.c` gives the sensor a valid power-on default.

The screen property fails for an unrelated reason: `bus_busy()` is
non-deterministic and may hold forever, so the refresh can be deferred
indefinitely. Making it provable needs a fairness assumption, which is
Exercise 3(e).

## Regenerating the monitors

The monitors are committed, so libltl2ba is only needed to change them. Use the
**negated** formula to ask whether a property holds — ESBMC does not negate it
for you.

```bash
ltl2ba -O c -H '"plant.h"' -f '!G({pressure > 500} -> F {valve_open})' > valve-neg.ba-2.c
```
