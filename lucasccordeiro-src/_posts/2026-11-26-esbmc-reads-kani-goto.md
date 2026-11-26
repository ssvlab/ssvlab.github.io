---
layout: post
title: "ESBMC on the Rust standard library: where a second engine helps and where it falls short"
date: 2026-11-26
author: Lucas C. Cordeiro and Rafael Sá Menezes
description: We ran ESBMC on all 1,888 Kani harnesses of the verify-rust-std challenge. It agrees with Kani on 94.9% of them with no wrong verdict and struggles on slices and pointer-heavy code. This post looks at where ESBMC helps Rust verification, where it does not yet, and what would change that.
tags: [formal-verification, esbmc, rust, kani]
categories: [research]
related_posts: false
---

Rust's safety guarantees rest on two things being correct: the compiler's checks, and the `unsafe` code those checks cannot see. Safe Rust is safe only if every library built on `unsafe` code meets conditions that the compiler never checks {% cite jung2018rustbelt --file blog --style ieee %}, and the compiler has soundness holes of its own: one in lifetime checking, open since 2015, lets safe code create a dangling reference ([rust-lang/rust#25860](https://github.com/rust-lang/rust/issues/25860)). Much of that `unsafe` code sits in the standard library, where abstractions such as `Vec`, `String`, slices, `NonNull`, and integer operations build safe APIs on top of raw pointer manipulation, uninitialised memory, compiler intrinsics, and other operations that require explicit safety guarantees {% cite qin2020understanding --file blog --style ieee %}. Memory-safety bugs have been found there too {% cite xu2022memory --file blog --style ieee %}, such as a buffer overflow in `VecDeque::reserve` ([CVE-2018-1000657](https://nvd.nist.gov/vuln/detail/CVE-2018-1000657)), and a bug in the standard library can affect every program that relies on it. Kani and ESBMC do not trust the borrow checker: they check memory safety on the compiled program, in safe and `unsafe` code alike.

The [Verifying the Rust Standard Library](https://github.com/model-checking/verify-rust-std) challenge, run by the Rust Foundation, turns that code into proof obligations {% cite cook2026verifying --file blog --style ieee %}. Most of its proofs so far are Kani harnesses, and ESBMC {% cite dantas2026esbmc --style ieee %} is one of the five tools the challenge's repository lists. ESBMC's `--binary` option, which loads a pre-compiled GOTO program, has been around for more than a decade; since v8.4 it also reads the CBMC GOTO binaries that Kani writes, so ESBMC checks the same harnesses as Kani without any translation.

Of the 1,888 harnesses in the repository, ESBMC agrees with Kani on 1,792 (94.9%), at 900 s and 15 GB per harness. It reports no false alarm and misses no bug. On the other 96 it runs out of time or memory, and most of those are slices and pointer-heavy code that Kani verifies. The rest of this post looks at where ESBMC helps Rust verification, where it does not yet, and what would change that.

## From a Rust harness to a GOTO binary

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

## How we measured

- **Harnesses:** all 1,888 in verify-rust-std at the merge of [#766](https://github.com/model-checking/verify-rust-std/pull/766), compiled by the Kani commit the challenge's CI pins (`53cb531`). 1,236 are contract harnesses like the one above and 652 are plain `#[kani::proof]` harnesses.
- **Reference:** Kani's own CI run on the same commit verifies all 1,888 as expected. For 1,772 that means success; for the other 116 it means a failing check, for example because the harness is marked `should_panic`. "Agree" means ESBMC's verdict matches Kani's. A *false alarm* is a `FAILED` where Kani expects success; a *missed bug* is a `SUCCESSFUL` where Kani expects a failure.
- **Limits:** 900 s and 15 GB per harness, one core, under BenchExec on an AWS r7a.16xlarge instance, with ESBMC master `f39e88e17d` (November 26) in its default configuration for Kani binaries: k-induction (for a harness with a loop contract, an invariant cut checked by incremental BMC), with Kani's assumption that `malloc` succeeds.
- **Kani's back end, for timing:** the same binaries through the steps Kani runs after code generation (`goto-instrument` for contracts, then CBMC 6.11 with Kani's flags), on the same machine under the same limits (November 26). CBMC agrees with Kani's expected verdict on all 1,888 harnesses.

## Where ESBMC does well

**It gives no wrong answers on this corpus.** ESBMC reports no false alarm and no missed bug on any of the 1,888 harnesses. It finds all 116 expected failures, each with a counterexample trace. Agreement is similar for both kinds of harness: 1,175 of 1,236 contract harnesses (95.1%) and 617 of 652 plain proofs (94.6%).

**Most of `core` is covered.** Broken down by module:

| Module | Harnesses | Agree | No verdict |
|---|---|---|---|
| `num` | 604 | 602 (99.7%) | 2 |
| `intrinsics` | 394 | 381 (96.7%) | 13 |
| `ptr` | 383 | 374 (97.7%) | 9 |
| `slice` | 212 | 142 (67.0%) | 70 |
| `convert` | 190 | 190 (100%) | 0 |
| `mem` | 40 | 40 (100%) | 0 |
| `time` | 24 | 24 (100%) | 0 |
| `alloc` | 14 | 14 (100%) | 0 |
| `ffi` | 14 | 13 (92.9%) | 1 |
| 9 smaller modules | 13 | 12 | 1 |

## Speed on the same machine

Figure 2 compares ESBMC with Kani's back end harness by harness. A point below the diagonal is a harness on which ESBMC is faster.

<img src="{{ '/assets/img/blog/2026-11-26-esbmc-vs-cbmc-time.png' | relative_url }}" alt="Two log-log scatter plots of ESBMC CPU time against Kani's back end, one point per harness, slice harnesses in orange. Left: against CBMC's solving step alone, most points lie above the diagonal. Right: against Kani's whole pipeline including goto-instrument, points spread around the diagonal. In both, ESBMC's no-verdict harnesses sit on a line at 900 s." style="width:100%;height:auto;background:#fff;padding:8px;border-radius:4px">

*Figure 2. ESBMC CPU time against CBMC's solving step (left) and against Kani's whole post-codegen pipeline (right), on the same machine and limits. Orange points are `slice` harnesses, blue points all other modules. ESBMC's 96 undecided harnesses sit on the 900 s line.*

How it reads depends on what one counts. Against CBMC's solving step alone, ESBMC is slower on most harnesses: the median is 1.7 s for ESBMC against 0.4 s for CBMC, and CBMC is faster on 1,629 of the 1,790 harnesses both decide. Against Kani's whole pipeline the picture flips, and ESBMC is faster on 967 of 1,792, because `goto-instrument` takes a median 76% of Kani's time. That second comparison flatters ESBMC: much of the instrumentation step handles contracts, including the frame conditions (`modifies` clauses) that ESBMC never sees.

Where ESBMC is faster, it can be much faster. Of the 35 harnesses on which CBMC itself needs more than 10 s, ESBMC is faster on 19. The 128-bit multiplications in `num::nonzero` take ESBMC under 0.7 s and CBMC between 11 and 38 s, and `non_null_check_read` takes 5.4 s against 55.5 s.

## Where ESBMC falls short

**Slices.** `slice` is the one module where ESBMC lags: 142 of 212 (67%). Its 70 timeouts are most of the 96 harnesses without a verdict. On the same machine, CBMC decides all 96, with a median of 8.5 s of solving and a maximum of 340 s.

**Why ESBMC times out.** CBMC solves these 96 harnesses in seconds, so the difficulty lies in how ESBMC encodes them rather than in the harnesses themselves. Profiling the ESBMC runs points to four causes.

- *Pointer encoding (85 harnesses).* The time goes into the solver, not into symbolic execution: about 61,000 s of solving against 2,200 s of symex across the 96. Kani runs CBMC with `--object-bits 12`, so a pointer is an object number and an offset, and an integer-to-pointer cast is a zero extension. ESBMC gives each object its own address range, and every integer-to-pointer cast adds range constraints over every object. Rust's slice and pointer code does such casts often. On `check_transmute_slice_metadata`, symbolic execution takes 0.08 s, but the formula is 80 MB, and Bitwuzla needs 167 s (Z3 158 s) where CBMC needs 0.02 s.
- *Loop contracts (5).* Kani lowers `#[kani::loop_invariant(...)]` to a call of a generated closure. Until recently, ESBMC dropped invariants with side effects and unwound these loops instead, which left 13 harnesses undecided. Two pull requests fix this. [esbmc#11055](https://github.com/esbmc/esbmc/pull/11055) evaluates the closure where the invariant is checked, and [esbmc#11077](https://github.com/esbmc/esbmc/pull/11077) verifies a Kani harness that carries a loop contract by cutting the loop at its invariant (`--loop-invariant-check --incremental-bmc`) instead of by k-induction. ESBMC now proves 8 of the 13, the `NonZero` `checked_pow` and `saturating_pow` harnesses for `i64`, `isize`, `i128` and `u128`, in 4 s to 51 s. Of the other five, `check_right_shift`, `check_reverse` and `check_run_utf8_validation` still time out. `check_to_str` and `check_left_shift` set their own unwind bound, so the new default does not apply to them, and they run out of memory and time respectively.
- *Symbolic `memcpy` (6).* In these harnesses, the number of bytes `memcpy` copies is not a constant but depends on the harness's nondeterministic inputs. ESBMC copies such a block in one step only in some cases; otherwise it runs its C model of `memcpy`, a loop that copies one byte per iteration. With no fixed length, symbolic execution keeps unrolling that loop and does not finish within the time limit ([esbmc#11026](https://github.com/esbmc/esbmc/issues/11026)).
- *k-induction rarely gets its inductive step.* In 80 of the 96, ESBMC could not havoc what a loop writes through a pointer, dropped the inductive step and fell back to BMC with increasing bounds, re-solving at every step.

**More cores did not help.** Since the time goes into the solver, one way to cut it is to split the problem. With `--multi-property`, ESBMC checks each claim of a harness against its own, smaller formula instead of one formula for all of them, and `--parallel-solving` solves those formulas side by side. We gave each harness four cores to see whether that would recover the timeouts. It recovered none of the 104 that the ESBMC we first measured left undecided. Instead, 113 harnesses ran out of memory, 39 of which the default configuration decides, because each claim kept its own solver alive. ESBMC master now caps the number of workers ([esbmc#11047](https://github.com/esbmc/esbmc/pull/11047)). With that cap at its default, 26 of the 112 harnesses recovered, but 64 still ran out of memory: the default counted all 64 host CPUs rather than the 4 the run may use, which [esbmc#11064](https://github.com/esbmc/esbmc/pull/11064) fixes.

**What ESBMC does not support.** None of the following came up in this corpus, but they bound what ESBMC can be given.

- The reader accepts GOTO format version 6 only.
- It declines SIMD operations, `setjmp`, `va_start` and `__CPROVER_DYNAMIC_OBJECT` with an error rather than a wrong verdict.
- For contracts, `is_fresh` does not check separation between pointers.
- `modifies` clauses never reach ESBMC, because Kani's `--only-codegen` stops before `goto-instrument` turns them into checks.

## Opportunities

- **A pointer encoding for Kani binaries.** Kani's semantics already fix pointers to an object number and an offset. An encoding that exploits this for CBMC binaries targets 85 of the 96 harnesses, and most of the `slice` gap.
- **An inductive step that survives pointer writes.** In 80 of the 96, k-induction gave up its inductive step. Havocking the memory a loop writes through a pointer, instead of dropping the step, could let ESBMC prove these loops for every iteration count.

ESBMC does not replace Kani on the standard library: its solving is slower than CBMC's on most harnesses, and it leaves 96 undecided. What it adds is a second, independent answer on the same binaries, which so far agrees with Kani on every harness it decides. Most of the gap traces to one encoding decision, and we now know where it is.

## Join us

We are looking for PhD students, postdocs and collaborators interested in Rust verification, model checking and SMT. ESBMC is open source, and the CBMC reader, its regression tests and the roadmap documents are in [ESBMC master](https://github.com/esbmc/esbmc). If this interests you, email [Lucas Cordeiro](mailto:lucas.cordeiro@manchester.ac.uk) with a short note on what you would like to work on, or talk to the group first on our public [Zulip chat](https://systemsandsoftwaresecurity.zulipchat.com/join/6ajabxaurkcwl6tl3ify55jv/).

## References

<style>ul.bibliography{list-style:none;padding-left:0}ul.bibliography li{margin-bottom:.6em}</style>

{% bibliography --file papers --file blog --cited_in_order --style ieee --template bib_numbered --group_by none --bibliography_list_tag ul %}
