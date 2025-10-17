def double_sum(n: int):
    __ESBMC_assume(n >= 0)

    i = 0
    x = 0
    y = 0

    # Strong, solver-friendly invariants
    loop_invariant(0 <= i)
    loop_invariant(i <= n)

    # relational equalities (direct)
    loop_invariant(y == i)
    loop_invariant(x == 2 * i)

    # and their difference forms (sometimes easier for the solver)
    loop_invariant(x - 2 * i == 0)
    loop_invariant(y - i == 0)

    # also explicit non-negativity of the accumulators
    loop_invariant(x >= 0)
    loop_invariant(y >= 0)

    while i < n:
        y += 1
        x += 2
        i += 1

    # postcondition
    assert x == 2 * n
    assert y == n
    return x

double_sum(nondet_int())

