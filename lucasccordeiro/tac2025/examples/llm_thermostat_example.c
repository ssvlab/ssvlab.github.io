int temperature = 22;

int read_temp() {
  return temperature;
}

int main() {
  int temp = read_temp();
  if (temp < 20 || temp > 25) {
    __ESBMC_assert(0, "Temperature out of bounds!");
  }
  return 0;
}
