#include <assert.h>

int main () 
{
  int i = __VERIFIER_nondet_int ();
  int j = __VERIFIER_nondet_int ();
  int k = __VERIFIER_nondet_int ();
  int n = __VERIFIER_nondet_int ();
  __ESBMC_assume(k >= 0);
  __ESBMC_assume(n >= 0);
  i = 0;
  j = 0;
  __loop_invariant (i >= 0);
  __loop_invariant (j >= i);
  while (i <= n) 
  {
    i = (i + 1);
    j = (j + i);
  }
  assert ( ((i + (j + k)) > (2 * n)) );
}

