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
  double temp1 = 2*x - 3*y;
  double temp2 = x + 4*y;
  double f = relu(temp1) + relu(temp2);
  assert(f >= 2.745);
  return 0;
}
