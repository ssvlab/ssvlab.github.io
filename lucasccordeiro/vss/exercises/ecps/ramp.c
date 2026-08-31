/* Actuator ramp: the heater duty cycle rises by a fixed step each tick until
 * the commanded number of ticks has elapsed. */
#include <assert.h>
#define STEP 2                    /* duty increment per tick */

int main(int argc, char **argv) {
  long long int tick = 1, duty = 0;
  unsigned int ticks = 5;         /* ticks in this ramp */
  __ESBMC_assume(ticks >= 1);
  while (tick <= ticks) {
    duty = duty + STEP;
    tick++;
  }
  assert(duty == ticks * STEP);
}
