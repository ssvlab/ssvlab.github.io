int main() {
  int x = 5;
  __ESBMC_assert(x > 10, "x must be greater than 10");
  return 0;
}
