#include <assert.h>	
#include <pthread.h>
int n=0; //shared variable
pthread_mutex_t mutex;
void* P(void* arg) {
  int tmp, i=1;
  while (i<=10) {
    pthread_mutex_lock(&mutex);
    tmp = n;
    n = tmp + 1;
    pthread_mutex_unlock(&mutex);
    i++;
  }
  return NULL;
}
int main (void) {
  pthread_t id1, id2;
  pthread_mutex_init(&mutex, NULL);
  pthread_create(&id1, NULL, P, NULL);
  pthread_create(&id2, NULL, P, NULL);
  pthread_join(id1, NULL);
  pthread_join(id2, NULL);
  assert(n == 20);
}
