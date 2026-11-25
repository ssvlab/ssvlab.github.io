---
layout: post
title: "ESBMC on the Rust standard library: where a second engine helps and where it falls short"
date: 2026-11-25
author: Lucas C. Cordeiro and Rafael Sá Menezes
description: We ran ESBMC on all 1,888 Kani harnesses of the verify-rust-std challenge. It agrees with Kani on 94.5% of them with no wrong verdict and struggles on slices and pointer-heavy code. This post looks at where ESBMC helps Rust verification, where it does not yet, and what would change that.
tags: [formal-verification, esbmc, rust, kani]
categories: [research]
related_posts: false
---

Rust's safety guarantees come from its compiler. The type and borrow checkers rule out data races and dangling references, and bounds checks stop out-of-bounds accesses, but in `unsafe` code it is the programmer who must uphold the safety guarantees. Much of that `unsafe` code sits in the standard library, where abstractions such as `Vec`, `String`, slices, `NonNull`, and integer operations build safe APIs on top of raw pointer manipulation, uninitialised memory, compiler intrinsics, and other operations that require explicit safety guarantees. Verification checks rather than assumes them, which is especially important for `core`: a bug there can affect every program that relies on it.

The [Verifying the Rust Standard Library](https://github.com/model-checking/verify-rust-std) challenge, run by AWS with the support of the Rust Foundation, turns that code into proof obligations {% cite cook2026verifying --file blog --style ieee %}. Most of its proofs so far are Kani harnesses, and ESBMC {% cite dantas2026esbmc --style ieee %} is one of the five tools the challenge accepts. Since ESBMC v8.4 we've had `esbmc --binary`, which can read Kani's CBMC binaries directly, so ESBMC checks the same harnesses as Kani without any translation.

That makes a direct comparison possible, and we ran one. Of the 1,888 harnesses in the repository, ESBMC agrees with Kani on 1,784 (94.5%), at 900 s and 15 GB per harness. It reports no false alarm and misses no bug. On the other 104 it runs out of time or memory, and most of those are slices and pointer-heavy code that Kani finishes in seconds. The rest of this post looks at where ESBMC helps Rust verification, where it does not yet, and what would change that.

## One harness, two back ends

Here is one of the challenge's harnesses. `unchecked_mul` on the integer types multiplies without an overflow check, and the result is undefined behaviour if the product overflows. A `requires` clause states when a call is safe (`library/core/src/num/int_macros.rs`), and a macro in `library/core/src/num/mod.rs` generates one harness per integer type. For `i8` it expands to:

```text
#[requires(!self.overflowing_mul(rhs).1)]
pub const unsafe fn unchecked_mul(self, rhs: Self) -> Self
```

```rust
#[kani::proof_for_contract(i8::unchecked_mul)]
pub fn checked_unchecked_mul_i8() {
    let num1: i8 = kani::any::<i8>();
    let num2: i8 = kani::any::<i8>();
    unsafe {
        num1.unchecked_mul(num2);
    }
}
```

Kani's compiler takes each harness in MIR (Mid-level Intermediate Representation), the simplified form of Rust that the Rust compiler uses for borrow checking and optimisation, and translates it into a CBMC GOTO binary. Everything specific to Rust is settled in that translation: how each type is laid out in memory, and where each overflow and bounds check goes. Kani hands the binary to CBMC. ESBMC reads the same file.

<img src="{{ '/assets/img/blog/2026-11-25-esbmc-kani-pipeline.svg' | relative_url }}" alt="A Rust harness goes through kani-compiler to a CBMC GOTO binary, harness.out. Two back ends read the binary: Kani's own (goto-instrument and CBMC) and ESBMC through esbmc --binary." style="width:100%;height:auto;background:#fff;padding:8px;border-radius:4px">

*Figure 1. Kani compiles each harness to a CBMC GOTO binary. CBMC is Kani's back end; ESBMC reads the same binary.*

Reading the bytes was the easy part. To give the same answers as Kani, ESBMC also has to interpret the binary the way Kani does. Kani inserts `reachability_check` and `cover` assertions that are meant to fail and reads them as information, so ESBMC now reports them apart from the verdict ([esbmc#10877](https://github.com/esbmc/esbmc/pull/10877)). Kani runs CBMC with `--no-malloc-may-fail`, so ESBMC assumes `malloc` succeeds when it sees Kani's `__KANI_` symbols in a binary ([esbmc#10975](https://github.com/esbmc/esbmc/pull/10975)). And many harnesses have loops with no bound, so ESBMC verifies a Kani binary by k-induction unless the command line chooses otherwise ([esbmc#10942](https://github.com/esbmc/esbmc/pull/10942)).

## How we measured

- **Harnesses:** all 1,888 in verify-rust-std at the merge of [#766](https://github.com/model-checking/verify-rust-std/pull/766), compiled by the Kani commit the challenge's CI pins (`53cb531`). 1,236 are contract harnesses like the one above and 652 are plain `#[kani::proof]` harnesses.
- **Reference:** Kani's own CI run on the same commit verifies all 1,888 as expected. For 1,772 that means success; for the other 116 it means a failing check, for example because the harness is marked `should_panic`. "Agree" means ESBMC's verdict matches Kani's. A *false alarm* is a `FAILED` where Kani expects success; a *missed bug* is a `SUCCESSFUL` where Kani expects a failure.
- **Limits:** 900 s and 15 GB per harness, one core, under BenchExec on an AWS r7a.16xlarge instance, with ESBMC master `03233ba208` (November 24) in its default configuration for Kani binaries.

## Where ESBMC does well

**It gives no wrong answers on this corpus.** ESBMC reports no false alarm and no missed bug on any of the 1,888 harnesses. It finds all 116 expected failures, each with a counterexample trace. Agreement is the same for both kinds of harness: 1,167 of 1,236 contract harnesses (94.4%) and 617 of 652 plain proofs (94.6%).

**Most of `core` is covered.** Broken down by module:

| Module | Harnesses | Agree | No verdict |
|---|---|---|---|
| `num` | 604 | 594 (98.3%) | 10 |
| `intrinsics` | 394 | 381 (96.7%) | 13 |
| `ptr` | 383 | 374 (97.7%) | 9 |
| `slice` | 212 | 142 (67.0%) | 70 |
| `convert` | 190 | 190 (100%) | 0 |
| `mem` | 40 | 40 (100%) | 0 |
| `time` | 24 | 24 (100%) | 0 |
| `alloc` | 14 | 14 (100%) | 0 |
| `ffi` | 14 | 13 (92.9%) | 1 |
| 11 smaller modules | 13 | 12 | 1 |

On the harnesses it decides, ESBMC is quick in absolute terms: roughly 1,600 finish in under ten seconds of CPU time, and about 850 in under one.

## Where ESBMC falls short

**Slices.** `slice` is the one module where ESBMC lags: 142 of 212 (67%). Its 70 timeouts are most of the 104 harnesses without a verdict. Kani verifies every one of the 104, with a median of 8.8 s and a maximum of 293 s on the challenge's CI runners.

**Speed.** ESBMC is the slower engine. On the harnesses where both agree, ESBMC's median is about 1.8 s of CPU time against 0.3 s of verification time for Kani. The machines and the clocks differ, so the ratio is only indicative, but the direction is clear.

**Why.** We traced the 104 to four causes.

- *Pointer encoding (85 harnesses).* The time goes into the solver, not into symbolic execution: about 68,000 s of solving against 3,000 s of symex across the 104. Kani runs CBMC with `--object-bits 12`, so a pointer is an object number and an offset, and an integer-to-pointer cast is a zero extension. ESBMC gives each object its own address range, and every integer-to-pointer cast adds range constraints over every object. Rust's slice and pointer code does such casts often. On `check_transmute_slice_metadata`, symbolic execution takes 0.08 s, but the formula is 80 MB, and Bitwuzla needs 167 s (Z3 158 s) where CBMC needs 0.02 s.
- *Loop contracts (13).* Kani lowers `#[kani::loop_invariant(...)]` to a call of a generated closure, and ESBMC drops invariants with side effects, so it unwinds these loops instead ([esbmc#11051](https://github.com/esbmc/esbmc/issues/11051)).
- *Symbolic `memcpy` (6).* A copy with a symbolic length that ESBMC's bounded `memcpy` model does not cover falls back to a byte loop that does not terminate in symbolic execution ([esbmc#11026](https://github.com/esbmc/esbmc/issues/11026)).
- *k-induction rarely gets its inductive step.* In 82 of the 104, ESBMC could not havoc what a loop writes through a pointer, dropped the inductive step and fell back to BMC with increasing bounds, re-solving at every step.

**More cores did not help.** Solving claims in parallel (`--parallel-solving --multi-property`, 4 cores per harness) recovered none of the 104. Instead, 113 harnesses ran out of memory, 39 of which the default configuration decides, because each claim kept its own solver alive. ESBMC master now caps the number of workers ([esbmc#11047](https://github.com/esbmc/esbmc/pull/11047)), and we are re-running this configuration to measure the effect.

**What ESBMC does not support.** None of the following came up in this corpus, but they bound what ESBMC can be given.

- The reader accepts GOTO format version 6 only.
- It declines SIMD operations, `setjmp`, `va_start` and `__CPROVER_DYNAMIC_OBJECT` with an error rather than a wrong verdict.
- For contracts, `is_fresh` does not check separation between pointers.
- `modifies` clauses never reach ESBMC, because Kani's `--only-codegen` stops before `goto-instrument` turns them into checks.
- With `--ir` (unbounded integers), ESBMC aborts on Kani binaries that cast a struct to an integer, as `NonNull::dangling()` does ([esbmc#11023](https://github.com/esbmc/esbmc/issues/11023)). The default bit-vector encoding handles the same binaries.

## Opportunities

- **A pointer encoding for Kani binaries.** Kani's semantics already fix pointers to an object number and an offset. An encoding that exploits this for CBMC binaries targets 85 of the 104 harnesses, and most of the `slice` gap.
- **Kani loop contracts.** Evaluating the generated closure where the invariant is checked (#11051) would let ESBMC use the 13 invariants instead of unwinding.
- **An inductive step that survives pointer writes.** In 82 of the 104, k-induction gave up its inductive step. Havocking the memory a loop writes through a pointer, instead of dropping the step, could let ESBMC prove these loops for every iteration count.

ESBMC does not replace Kani on the standard library: it is slower and leaves 104 harnesses undecided. What it adds is a second, independent answer on the same binaries, which so far agrees with Kani on every harness it decides. Most of the gap traces to one encoding decision, and we now know where it is.

## Join us

We are looking for PhD students, postdocs and collaborators interested in Rust verification, model checking and SMT. ESBMC is open source, and the CBMC reader, its regression tests and the roadmap documents are in [ESBMC master](https://github.com/esbmc/esbmc). If this interests you, email [Lucas Cordeiro](mailto:lucas.cordeiro@manchester.ac.uk) with a short note on what you would like to work on, or talk to the group first on our public [Zulip chat](https://systemsandsoftwaresecurity.zulipchat.com/join/6ajabxaurkcwl6tl3ify55jv/).

## References

<style>ul.bibliography{list-style:none;padding-left:0}ul.bibliography li{margin-bottom:.6em}</style>

{% bibliography --file papers --file blog --cited_in_order --style ieee --template bib_numbered --group_by none --bibliography_list_tag ul %}
