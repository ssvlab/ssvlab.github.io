#include <pthread.h>

int x=0;

void *t1(void *arg)
{
  x++;  // a1
  // x = x + 1
  // ld r1, x1 <- load de x para r1
  // ld r2, 1
  // add r3, r1, r2
  // st x1, r3
  x++;  // b1
}

void *t2(void *arg)
{
  x--; // a2 
  x--; // b2
}

int main()
{
  pthread_t id1, id2;

  pthread_create(&id1, NULL, t1, NULL); //t1
  pthread_create(&id2, NULL, t2, NULL); //t2

  return 0;
}
