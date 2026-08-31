/* T and P hand their samples to S over a single-word display bus. Only one
 * task may drive the bus at a time; Peterson's algorithm arbitrates.
 * in_T / in_P record which task currently owns it.
 */
#include <pthread.h>

int want[2];          /* task i is requesting the bus */
int turn;
int in_T, in_P;       /* task i is driving the bus    */
int bus_word;         /* the sample currently on the bus */

void *task_T(void *arg) {
  want[0] = 1;
  turn = 1;
  while (want[1] && turn == 1) {}
  in_T = 1;
  bus_word = 1;       /* temperature sample */
  in_T = 0;
  want[0] = 0;
  return 0;
}

void *task_P(void *arg) {
  want[1] = 1;
  turn = 0;
  while (want[0] && turn == 0) {}
  in_P = 1;
  bus_word = 2;       /* pressure sample */
  in_P = 0;
  want[1] = 0;
  return 0;
}

int main(void) {
  pthread_t t, p;
  pthread_create(&t, NULL, task_T, NULL);
  pthread_create(&p, NULL, task_P, NULL);
  return 0;
}
