#include <pthread.h>
#include <assert.h>

int i, x, flag[2];
_Bool turn, c1, c2;

void *t1(void *arg) {
  flag[0] = 1;
  turn = 1;
  while (flag[1] == 1 && turn == 1) {};
  //critical section
  c1=1;
  CT0: if (i==1) x=1;
  c1=0;
  //end of critical section
  flag[0] = 0;
  return NULL;
}

void *t2(void *arg) {
  flag[1] = 1;
  turn = 0;
  while (flag[0] == 1 && turn == 0) {};
  //critical section
  c2=1;
  CT1: if (i==2) x=2;
  c2=0;
  //end of critical section
  flag[1] = 0;
  return NULL;
}

int main()
{
  pthread_t id1, id2;

  c1 = 0;
  c2 = 0;

  i = nondet_int();
  turn = nondet_bool();

  pthread_create(&id1, NULL, t1, NULL);
  pthread_create(&id2, NULL, t2, NULL);

  // Property 1: M ⊨ G ¬ ( C1 ∧ C2)
  // At most, one process in the critical region at any time.
  assert(!c1 || !c2);
  // The assertion below does not hold
  //assert(c1 && c2);

  // Property 2: M ⊨ G (( T1→FC1 )∧(T2→FC2 )) 
  // Whenever a process tries to enter its critical region, it will eventually succeed.
  // $ esbmc mutual-exclusion.c --unwind 3 --context-bound 3 --no-unwinding-assertions --compact-trace --error-label CT0

  return 0;
}
