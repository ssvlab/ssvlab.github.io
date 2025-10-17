int main()
{
  int status = 0;
  while(__VERIFIER_nondet_int())
  {
    if(!status)
      status = 1;
    else if(status == 1)
      status = 2;
  }

  while(1)
    __ESBMC_assert(status != 3, "");

  return 0;
}
