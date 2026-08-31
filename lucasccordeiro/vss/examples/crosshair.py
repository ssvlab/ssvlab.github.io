def double_sum(n: int) -> int:
    __ESBMC_assume(n >= 0)

    i = 0
    x = 0
    y = 0

    # A single conjunction: bounds plus the relational equalities that tie the
    # accumulators to the counter. This is what makes the postcondition follow
    # from the invariant alone, without unwinding the loop.
    __loop_invariant(0 <= i and i <= n and y == i and x == 2 * i)
    while i < n:
        y += 1
        x += 2
        i += 1

    assert x == 2 * n
    assert y == n
    return x

double_sum(nondet_int())
