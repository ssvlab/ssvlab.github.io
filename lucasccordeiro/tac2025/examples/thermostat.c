int temperature = 25;

int read_sensor() {
  return temperature;
}

int main() {
  int t = read_sensor();
  if (t > 30) {
    __ESBMC_assert(0, "Overheating!");
  }
  return 0;
}
