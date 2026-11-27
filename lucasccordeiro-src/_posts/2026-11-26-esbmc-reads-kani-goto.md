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

Amazon's Rust verifier, Kani, has 1,888 proof harnesses for the Rust standard library, and every verdict they give comes from one engine, CBMC. A bug there could let a wrong proof through, and nothing else in Kani's pipeline would catch it. ESBMC, the open-source model checker our group develops for C, C++ and other languages, can read the binaries Kani builds, so we ran it on the same harnesses. It encodes pointers differently and solves with SMT rather than CBMC's SAT back end, which makes it an independent check. We wanted to know two things: does it reach the same verdicts, and where it does not, what is missing?

The short answers: on 1,792 of 1,888 harnesses (94.9%) it agrees with Kani, and it never contradicts it. Most of the rest traces to one design decision, how ESBMC encodes pointers, and that same decision turns out to be what gets address-dependent Rust right.

## Why the standard library

Safe Rust is safe only if every library built on `unsafe` code meets conditions the compiler never checks {% cite jung2018rustbelt --file blog --style ieee %}. A large share of that code lives in the standard library, where `Vec`, `String`, slices and `NonNull` build safe APIs on raw pointers, uninitialized memory and compiler intrinsics {% cite qin2020understanding --file blog --style ieee %}. Bugs there are real. Memory-safety bugs have been found in it {% cite xu2022memory --file blog --style ieee %}, including a buffer overflow in `VecDeque::reserve` ([CVE-2018-1000657](https://nvd.nist.gov/vuln/detail/CVE-2018-1000657)), and the compiler has soundness holes of its own: one, open since 2015, lets safe code create a dangling reference ([rust-lang/rust#25860](https://github.com/rust-lang/rust/issues/25860)). Kani and ESBMC check the compiled program, so they catch pointer misuse in `unsafe` code that the borrow checker never sees. Neither checks Rust's aliasing rules themselves, which [Kani's documentation](https://model-checking.github.io/kani/soundness.html) lists as out of scope.

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

Profiling the 96 runs points to one dominant cause and three others.

The dominant one is how pointers are encoded, and it accounts for 85 harnesses. The challenge's CI runs Kani with `--object-bits 12` (Kani's default is 16): a pointer is an object number and an offset, and casting an integer to a pointer is a zero extension. ESBMC gives each object its own address range instead, so every integer-to-pointer cast adds range constraints over every object in the program, and Rust's slice and pointer code casts constantly. The time goes into the solver (about 61,000 s of solving against 2,200 s of symbolic execution across the 96). `check_transmute_slice_metadata` shows the shape: symbolic execution takes 0.08 s, the formula is 80 MB, and Bitwuzla needs 167 s (Z3, 158 s) for what CBMC solves in 0.02 s.

The other three causes are each tied to a specific construct. Six harnesses copy a symbolic number of bytes with `memcpy`, which ESBMC's C model unrolls one byte at a time until the clock runs out ([esbmc#11026](https://github.com/esbmc/esbmc/issues/11026)). Five carry loop contracts that ESBMC still cannot turn into a proof; there were 13 until [esbmc#11055](https://github.com/esbmc/esbmc/pull/11055) and [esbmc#11077](https://github.com/esbmc/esbmc/pull/11077) taught ESBMC to read Kani's invariants and to cut the loop at them, which now proves the `NonZero` `checked_pow` and `saturating_pow` harnesses for `i64`, `isize`, `i128` and `u128` in 4 s to 51 s. And in 80 of the 96, k-induction gives up its inductive step because it cannot havoc what a loop writes through a pointer, so it falls back to BMC with growing bounds and re-solves at every step.

## The slow encoding is the sound one

CBMC, as Kani runs it, puts every object at a fixed address: the object number in the top bits (12 in the challenge's CI, 16 by default), then the offset. That is all it needs to check that each access stays inside its object, and it is why integer-to-pointer casts cost it nothing. It also means Kani checks address-dependent code against one memory layout, in which every object is aligned to a large power of two (2^52 bytes with 12 object bits) and the objects sit in a fixed order. ESBMC leaves each object's address open, within what the platform guarantees, and pays for that in the solver.

Two small harnesses show the difference. Both assertions are false on real hardware: the allocator only has to honor the type's alignment, one byte for `u8`, and Rust says nothing about the order of statics.

```rust
#[kani::proof]
fn box_is_page_aligned() {
    let b = Box::new(0u8);
    let addr = &*b as *const u8 as usize;
    assert!(addr % 4096 == 0);
}

static A: u8 = 1;
static B: u8 = 2;

#[kani::proof]
fn statics_are_ordered() {
    assert!((&A as *const u8 as usize) < (&B as *const u8 as usize));
}
```

Kani 0.68.0, with its default settings, reports both as VERIFICATION SUCCESSFUL. ESBMC, reading the GOTO binaries Kani built for them, reports both as VERIFICATION FAILED, each with a counterexample. The standard library has real code of this kind, such as `align_offset` and the alignment checks in `ptr` and `slice`. Among the 1,792 harnesses ESBMC decides, it agrees with Kani on every one, so the difference exposed no wrong proof in the library; we cannot say the same for the 96 it does not decide.

## What we learned

The part that costs time can be the part that is right. Most of ESBMC's timeouts come from an address model that refuses to assume a layout, and that same model catches the address bugs Kani's layout hides. Copying Kani's encoding would buy speed and lose that.

## What comes next

The first step is to make ESBMC's address model cheaper without changing what it guarantees. Each time Rust code turns an integer back into a pointer, ESBMC considers every object in the program as a possible target, and that is where the time goes on 85 of the 96 undecided harnesses and most of the `slice` gap. The second is k-induction: in 80 of the 96, it cannot account for what a loop writes through a pointer, so it drops its inductive step and can prove the loop only by unwinding it completely. Neither is a small patch, and we would rather do the first one well than both badly.

More cores are not a shortcut. Splitting each harness into one formula per claim and solving them on four cores (`--multi-property --parallel-solving`) decided none of the undecided harnesses and ran 113 out of memory; [esbmc#11047](https://github.com/esbmc/esbmc/pull/11047) and [esbmc#11064](https://github.com/esbmc/esbmc/pull/11064) now cap the workers.

## Join us

We are looking for PhD students, postdocs and collaborators interested in Rust verification, model checking and SMT. ESBMC is open source, and the CBMC reader, its regression tests and the roadmap documents are in [ESBMC master](https://github.com/esbmc/esbmc). If this interests you, email [Lucas Cordeiro](mailto:lucas.cordeiro@manchester.ac.uk) with a short note on what you would like to work on, or talk to the group first on our public [Zulip chat](https://systemsandsoftwaresecurity.zulipchat.com/join/6ajabxaurkcwl6tl3ify55jv/).

## References

<style>ul.bibliography{list-style:none;padding-left:0}ul.bibliography li{margin-bottom:.6em}</style>

{% bibliography --file papers --file blog --cited_in_order --style ieee --template bib_numbered --group_by none --bibliography_list_tag ul %}
