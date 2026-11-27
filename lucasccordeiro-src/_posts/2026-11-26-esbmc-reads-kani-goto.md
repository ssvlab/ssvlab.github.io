---
layout: post
title: "Verifying Rust's standard library with ESBMC"
date: 2026-11-26
author: Lucas C. Cordeiro and Rafael Sá Menezes
description: Every Kani proof of the Rust standard library rests on one engine, CBMC. We checked all 1,888 of them with ESBMC, on the same binaries. It agrees on 94.9% with no wrong verdict; getting there taught us where a second engine's cost really lies.
tags: [formal-verification, esbmc, rust, kani]
categories: [research]
related_posts: false
---

Amazon's Rust verifier, Kani, has 1,888 proof harnesses for the Rust standard library, and every verdict they give comes from one engine, CBMC. A bug there could let a wrong proof through, and nothing else in Kani's pipeline would catch it. So we fed the same GOTO binaries Kani builds to ESBMC, a model checker that encodes pointers differently and solves with SMT rather than CBMC's SAT back end, and asked two things: does it reach the same verdicts, and where it does not, what is missing?

The short answers: on 1,792 of 1,888 harnesses (94.9%) it agrees with Kani, and it never contradicts it. Closing the rest is mostly a matter of one encoding decision, and the comparison taught us more about how to measure a verifier than we expected.

## Why the standard library

Safe Rust is safe only if every library built on `unsafe` code meets conditions the compiler never checks {% cite jung2018rustbelt --file blog --style ieee %}. A large share of that code lives in the standard library, where `Vec`, `String`, slices and `NonNull` build safe APIs on raw pointers, uninitialized memory and compiler intrinsics {% cite qin2020understanding --file blog --style ieee %}. Bugs there are real. Memory-safety bugs have been found in it {% cite xu2022memory --file blog --style ieee %}, including a buffer overflow in `VecDeque::reserve` ([CVE-2018-1000657](https://nvd.nist.gov/vuln/detail/CVE-2018-1000657)), and the compiler has soundness holes of its own: one, open since 2015, lets safe code create a dangling reference ([rust-lang/rust#25860](https://github.com/rust-lang/rust/issues/25860)). So both Kani and ESBMC check the compiled program and trust neither the borrow checker nor the library.

The [Verifying the Rust Standard Library](https://github.com/model-checking/verify-rust-std) challenge, run by the Rust Foundation, turns that code into proof obligations {% cite cook2026verifying --file blog --style ieee %}. Most of its proofs so far are Kani harnesses. ESBMC {% cite dantas2026esbmc --style ieee %} is one of the five tools the challenge's repository lists, and since v8.4 its `--binary` option reads the CBMC GOTO binaries Kani writes. That is what made the experiment cheap to set up: no translation, the same file for both tools.

## The setup

Here is one of the challenge's harnesses. `unchecked_mul` multiplies without an overflow check, so a product that overflows is undefined behavior. A `requires` clause says when a call is safe, and a macro generates one harness per integer type; for `i8`:

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

Kani's compiler translates each harness from MIR, the form of Rust the compiler uses for borrow checking, into a CBMC GOTO binary. Everything specific to Rust is settled in that step: how each type is laid out in memory, and where each overflow and bounds check goes. Kani then hands the binary to CBMC, and ESBMC reads the same file (Figure 1).

<img src="{{ '/assets/img/blog/2026-11-25-esbmc-kani-pipeline.svg' | relative_url }}" alt="A Rust harness goes through kani-compiler to a CBMC GOTO binary, harness.out. Two back ends read the binary: Kani's own (goto-instrument and CBMC) and ESBMC through esbmc --binary." style="width:100%;height:auto;background:#fff;padding:8px;border-radius:4px">

*Figure 1. Kani compiles each harness to a CBMC GOTO binary. CBMC is Kani's back end; ESBMC reads the same binary.*

We took all 1,888 harnesses in verify-rust-std at the merge of [#766](https://github.com/model-checking/verify-rust-std/pull/766), compiled by the Kani commit the challenge's CI pins (`53cb531`): 1,236 contract harnesses like the one above and 652 plain `#[kani::proof]` harnesses. Kani's own CI verifies all 1,888 as expected, which means success for 1,772 and a failing check for the other 116 (for example, a harness marked `should_panic`). Each tool got 900 s and 15 GB per harness on one core, under BenchExec on an AWS r7a.16xlarge instance. ESBMC ran master `f39e88e17d` (November 26) with its defaults for Kani binaries: k-induction, or for a harness with a loop contract an invariant cut checked by incremental BMC, and Kani's assumption that `malloc` succeeds.

## ESBMC agrees, and never contradicts

ESBMC agrees with Kani on 1,792 harnesses. It reports no false alarm and misses no bug: all 116 expected failures come back `FAILED`, each with a counterexample trace. That is the result we cared about most. On this corpus, an engine that encodes memory differently and talks to different solvers found nothing wrong with Kani's verdicts.

Agreement barely depends on the kind of harness (1,175 of 1,236 contract harnesses, 617 of 652 plain proofs), but it depends a lot on the module:

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

The other 96 harnesses run out of time (95) or memory (1). Seventy of them are in `slice`. CBMC decides all 96 on the same machine, with a median of 8.5 s and a maximum of 340 s, so these are not hard problems. They are hard for ESBMC.

## Why ESBMC gets stuck

Profiling the 96 runs points to one dominant cause and three smaller ones.

The dominant one is how pointers are encoded, and it accounts for 85 harnesses. Kani runs CBMC with `--object-bits 12`: a pointer is an object number and an offset, and casting an integer to a pointer is a zero extension. ESBMC gives each object its own address range instead, so every integer-to-pointer cast adds range constraints over every object in the program, and Rust's slice and pointer code casts constantly. The time goes into the solver (about 61,000 s of solving against 2,200 s of symbolic execution across the 96). `check_transmute_slice_metadata` shows the shape: symbolic execution takes 0.08 s, the formula is 80 MB, and Bitwuzla needs 167 s (Z3, 158 s) for what CBMC solves in 0.02 s.

The smaller causes are more mundane. Six harnesses copy a symbolic number of bytes with `memcpy`, which ESBMC's C model unrolls one byte at a time until the clock runs out ([esbmc#11026](https://github.com/esbmc/esbmc/issues/11026)). Five carry loop contracts that ESBMC still cannot turn into a proof; there were 13 until [esbmc#11055](https://github.com/esbmc/esbmc/pull/11055) and [esbmc#11077](https://github.com/esbmc/esbmc/pull/11077) taught ESBMC to read Kani's invariants and to cut the loop at them, which now proves the `NonZero` `checked_pow` and `saturating_pow` harnesses for `i64`, `isize`, `i128` and `u128` in 4 s to 51 s. And in 80 of the 96, k-induction gives up its inductive step because it cannot havoc what a loop writes through a pointer, so it falls back to BMC with growing bounds and re-solves at every step.

## A fairer speed comparison

Our first timing comparison put ESBMC against CBMC on the binaries each tool normally sees (Figure 2). Against CBMC's solving step alone, ESBMC is slower: a median of 1.7 s against 0.4 s, and CBMC is faster on 1,629 of the 1,790 harnesses both decide. Against Kani's whole pipeline, which spends a median 76% of its time in `goto-instrument` before CBMC starts, ESBMC came out faster on 967 of 1,792. There are real wins in there, too: the 128-bit multiplications in `num::nonzero` take ESBMC under 0.7 s and CBMC 11 to 38 s.

<img src="{{ '/assets/img/blog/2026-11-26-esbmc-vs-cbmc-time.png' | relative_url }}" alt="Two log-log scatter plots of ESBMC CPU time against Kani's back end, one point per harness, slice harnesses in orange. Left: against CBMC's solving step alone, most points lie above the diagonal. Right: against Kani's whole pipeline including goto-instrument, points spread around the diagonal. In both, ESBMC's no-verdict harnesses sit on a line at 900 s." style="width:100%;height:auto;background:#fff;padding:8px;border-radius:4px">

*Figure 2. ESBMC CPU time against CBMC's solving step (left) and against Kani's whole post-codegen pipeline (right), on the same machine and limits. Orange points are `slice` harnesses, blue points all other modules. ESBMC's 96 undecided harnesses sit on the 900 s line.*

That 967 bothered us, because the two tools were not reading the same program. CBMC checks what `goto-instrument` produces: one harness, trimmed of unused functions, with contracts already turned into checks. ESBMC was reading the raw binary from code generation, which carries the whole crate and skips `goto-instrument` altogether. So we ran ESBMC on the binaries CBMC checks, after Kani's full post-codegen pipeline.

The first attempt failed on every contract harness. CBMC's contract instrumentation (DFCC) allocates zero-filled memory and asks whether a pointer is to the heap, and ESBMC's CBMC reader supported neither. Chasing those gaps turned up two crashes as well, a comma inside a loop invariant and a unary plus, that segfaulted ESBMC on master. Five pull requests later ([esbmc#11108](https://github.com/esbmc/esbmc/pull/11108), [#11109](https://github.com/esbmc/esbmc/pull/11109), [#11113](https://github.com/esbmc/esbmc/pull/11113), [#11114](https://github.com/esbmc/esbmc/pull/11114) and [#11117](https://github.com/esbmc/esbmc/pull/11117), all merged), ESBMC master `c4a2d96f7e` reads the whole pipeline's output and agrees with Kani on 1,790 harnesses, again with no wrong verdict. Of the other 98, 95 time out, 1 runs out of memory, and 2 havoc a heap buffer with `__CPROVER_havoc_object`, which [esbmc#11127](https://github.com/esbmc/esbmc/pull/11127) handles. Against ESBMC on the raw binaries, the two inputs now nearly match: two harnesses that were out of reach agree (`check_to_str` and the `memcpy` harness `check_copy_from_slice_u64`), and four `write_bytes` harnesses that agreed now time out.

On byte-identical input the speed picture is plain. On the 1,788 harnesses both tools decide, CBMC's solver is faster on 1,731, with a median of 0.4 s against 1.4 s, and with both tools paying for `goto-instrument`, ESBMC is faster on 54. The contract harnesses' `modifies` clauses, which the raw binaries never carry, now reach ESBMC as checks too.

## What we learned

A second engine is cheap when it reads the same IR, but the IR's corners are where the work is. None of the fixes above touched ESBMC's solver or its symbolic execution. All five were in how ESBMC reads a CBMC binary: a built-in with a flag nobody had exercised, a heap test the contract library depends on, whole-object copies on heap buffers, and two operators that only appear inside loop invariants. Each fix was small, yet the first two alone had blocked every contract harness.

Compare tools on the same input. We would have published "ESBMC beats Kani's pipeline on 967 harnesses" if we had stopped at the first comparison. On identical binaries it wins on 54. Part of the gap is just loading: on one plain proof, ESBMC spent 5.3 s of its 5.7 s building and processing the whole crate's GOTO program and 5 ms solving, and on the trimmed binary the same harness takes about 1 s.

More cores did not buy time. Since the time goes into the solver, we tried splitting each harness into one formula per claim (`--multi-property`) and solving them in parallel on four cores (`--parallel-solving`). It recovered none of the harnesses ESBMC could not decide, and 113 ran out of memory instead, 39 of which the default configuration decides, because each claim kept its own solver alive. [esbmc#11047](https://github.com/esbmc/esbmc/pull/11047) and [esbmc#11064](https://github.com/esbmc/esbmc/pull/11064) now cap the workers, but the lesson stands: when the formula is the problem, more copies of it are not the answer.

Run the real corpus early. ESBMC's suite of CBMC-binary tests had about 430 programs, and none of them allocated zero-filled memory or asked `__CPROVER_DYNAMIC_OBJECT` the way CBMC's contract instrumentation does. One run of the 1,888 harnesses exposed both, and fixing them exposed the two crashes. The corpus also ranked the gaps for us: no synthetic test would have put the pointer encoding, at 85 harnesses, ahead of everything else.

## What comes next

The pointer encoding is the one change that would move the numbers. Kani's semantics already fix a pointer as an object number and an offset; an encoding that uses that for CBMC binaries targets 85 of the 96 undecided harnesses and most of the `slice` gap. After that, k-induction needs to havoc what a loop writes through a pointer instead of dropping its inductive step, which affects 80 of the 96. Neither is a small patch, and we would rather do the first one well than both badly.

## Join us

We are looking for PhD students, postdocs and collaborators interested in Rust verification, model checking and SMT. ESBMC is open source, and the CBMC reader, its regression tests and the roadmap documents are in [ESBMC master](https://github.com/esbmc/esbmc). If this interests you, email [Lucas Cordeiro](mailto:lucas.cordeiro@manchester.ac.uk) with a short note on what you would like to work on, or talk to the group first on our public [Zulip chat](https://systemsandsoftwaresecurity.zulipchat.com/join/6ajabxaurkcwl6tl3ify55jv/).

## References

<style>ul.bibliography{list-style:none;padding-left:0}ul.bibliography li{margin-bottom:.6em}</style>

{% bibliography --file papers --file blog --cited_in_order --style ieee --template bib_numbered --group_by none --bibliography_list_tag ul %}
