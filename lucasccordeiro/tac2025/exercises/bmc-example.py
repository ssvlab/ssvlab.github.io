def collatz (n: int) -> int:
  while n != 1:
    print(n, end = " -> ")
    if n % 2 == 0:
      n = n // 2
    else:
      n = 3 * n + 1
  print (1)

collatz (6) # This terminates
collatz (-1) # Non - terminating for invalid input (negative number)

