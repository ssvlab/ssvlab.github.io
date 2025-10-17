i = nondet_int()
j = nondet_int()
k = nondet_int()
n = nondet_int()

__ESBMC_assume(k >= 0)
__ESBMC_assume(n >= 0)

i = 0
j = 0

# Loop invariants
# invariant: i >= 0
# invariant: j >= i

__loop_invariant(i >= 0)
__loop_invariant(j >= i)
while i <= n:
    i = i + 1
    j = j + i

# Postcondition
assert (i + (j + k)) > (2 * n)

