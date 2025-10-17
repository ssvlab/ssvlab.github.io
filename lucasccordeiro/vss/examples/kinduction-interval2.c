int main()
{
  int a = nondet_int();
  
  while(a <= 100)
    a++;
  assert(a > 10);
  return 0;
}
