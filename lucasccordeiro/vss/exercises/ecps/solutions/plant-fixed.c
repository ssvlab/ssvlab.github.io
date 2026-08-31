/* Chemical-process controller of Figure 1, as a cyclic executive.
 *
 * Each round is one pass of the T, P and S processes: sample the two ADCs,
 * drive the heater switch and the pump/valve DAC, then refresh the screen.
 * The sensor readings are nondeterministic within their transducer ranges,
 * so one run covers every reading the hardware can produce.
 */

#define TEMP_LOW    20    /* heater on below this          */
#define TEMP_HIGH  300    /* heater off above this         */
#define PRESS_LOW  100    /* valve closed below this       */
#define PRESS_HIGH 500    /* valve open above this         */

#ifndef ROUNDS
#define ROUNDS 2
#endif

int temperature = 25;   /* power-on default: a valid nominal reading */
int pressure;
int heater_on, valve_open;
int fresh_sample, displayed;

int nondet_int(void);

static int read_thermocouple(void) {
  int t = nondet_int();
  __ESBMC_assume(t >= -50 && t <= 400);
  return t;
}

static int read_transducer(void) {
  int p = nondet_int();
  __ESBMC_assume(p >= 0 && p <= 600);
  return p;
}

static int bus_busy(void) {
  return nondet_int() != 0;
}

/* T: temperature control. */
static void process_T(void) {
  temperature = read_thermocouple();
  if (temperature < TEMP_LOW)
    heater_on = 1;
  else if (temperature > TEMP_HIGH)
    heater_on = 0;
}

/* P: pressure control. */
static void process_P(void) {
  pressure = read_transducer();
  if (pressure > PRESS_HIGH)
    valve_open = 1;
  else if (pressure < PRESS_LOW)
    valve_open = 0;
}

/* S: screen refresh. The display bus may be busy, in which case the refresh
 * is deferred to a later round -- so the handover is not instantaneous. */
static void process_S(void) {
  if (fresh_sample && !bus_busy()) {
    displayed = 1;
    fresh_sample = 0;
  }
}

int main(void) {
  heater_on = 0;
  valve_open = 0;
  fresh_sample = 0;
  displayed = 0;

  for (int round = 0; round < ROUNDS; round++) {
    process_T();
    process_P();
    fresh_sample = 1;
    displayed = 0;
    process_S();
    process_S();   /* the cyclic executive gives S two slots per round */
  }
  return 0;
}
