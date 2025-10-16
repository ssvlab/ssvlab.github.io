// esbmc neural-net.c --fixedbv
#include <assert.h>

double relu(double x)
{
  if (x>0)
    return x;
  else
    return 0;
}

int main()
{
  double x = 0.749, y = 0.498; 
  double nodeA = 2*x - 3*y;
  double nodeB = x + 4*y;
  double f = relu(nodeA) + relu(nodeB);
  assert(f >= 2.745);
  return 0;
}
