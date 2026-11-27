---
layout: post
title: "Verifying Rust's standard library with ESBMC"
date: 2026-11-27
author: Lucas C. Cordeiro and Rafael Sá Menezes
description: Every Kani proof of the Rust standard library rests on one engine, CBMC. We checked all 1,888 of them with ESBMC, on the same binaries. It agrees on 94.9% with no wrong verdict; getting there taught us where a second engine's cost really lies.
tags: [formal-verification, esbmc, rust, kani]
categories: [research]
related_posts: false
---

Safe Rust is safe only if every library built on `unsafe` is sound {% cite jung2018rustbelt --file blog --style ieee %}. This includes the standard library, where fundamental constructs such as `Vec` and `String` rely on raw pointers, uninitialized memory, and compiler intrinsics {% cite qin2020understanding --file blog --style ieee %}. Memory-safety bugs have been found in the standard library itself {% cite xu2022memory --file blog --style ieee %}, including a buffer overflow in `VecDeque::reserve` ([CVE-2018-1000657](https://nvd.nist.gov/vuln/detail/CVE-2018-1000657)), and the compiler has soundness holes of its own: one, open since 2015, lets safe code create a dangling reference ([rust-lang/rust#25860](https://github.com/rust-lang/rust/issues/25860)).

The [Verifying the Rust Standard Library](https://github.com/model-checking/verify-rust-std) challenge, run by the Rust Foundation, turns the standard library's unsafe code into proof obligations {% cite cook2026verifying --file blog --style ieee %}. Most of these proof obligations are currently verified through Kani. Kani uses CBMC as its backend and proof engine, and ESBMC supports its GOTO binary format {% cite dantas2026esbmc --style ieee %}.

Over the last few months, we've focused on improving compatibility between ESBMC and Kani. Currently, we can verify 1,792 out of the 1,888 (94.9%) harnesses. In all of those, ESBMC agrees with Kani's verdict. However, as we show later, performance differs.

In this post, we will show how ESBMC can complement a proof that CBMC has done. Specifically, ESBMC does not fix where objects are placed in memory, so when a property depends on addresses, a proof from ESBMC holds for every valid placement, not just one.

## A harness

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

We took all 1,888 harnesses in verify-rust-std at the merge of [#766](https://github.com/model-checking/verify-rust-std/pull/766), compiled by the Kani commit the challenge's CI pins (`53cb531`): 1,236 contract harnesses like the one above and 652 plain `#[kani::proof]` harnesses. Kani's own CI verifies all 1,888 as expected, which means success for 1,772 and a failing check for the other 116 (for example, a harness marked `should_panic`). Each tool was limited to 900 s and 15 GB per harness on one core under BenchExec. We used ESBMC with k-induction for most harnesses; for a harness with a loop contract, it replaces the loop with its invariant. Both tools assumed that `malloc` never fails.

## Results

ESBMC agrees with Kani on 1,792 harnesses and fails to reach a verdict on the others. Agreement barely depends on the kind of harness (1,175 of 1,236 contract harnesses, 617 of 652 plain proofs), but it depends a lot on the module:

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

The other 96 harnesses run out of time (95) or memory (1). Seventy of them are in `slice`. CBMC solves all 96 on the same machine, with a median of 8.5 s and a maximum of 340 s, so why is ESBMC struggling?

## ESBMC vs CBMC memory encodings

In 85 of the 96 harnesses, we attributed the slowdown to pointer encoding.

In CBMC, a pointer is a pair made of an object number and an offset.
In these harnesses, through "--object-bits 12", the top 12 bits of a 64-bit pointer hold the object number while the other 52 bits hold the offset.
The pointer's bits are the object number and offset, so `ptr as usize` is `object << 52 | offset`, and casting an integer back to a pointer splits it the same way.

ESBMC gives each object its own address range. Every integer-to-pointer cast adds range constraints over every object in the program, and Rust's slice and pointer code casts constantly.

In the end, a harness that took CBMC 0.02 s to solve takes 167 s with ESBMC. But what happens if the memory layout assumption is broken?

## Memory layout issues

The main limitation of the CBMC approach is that it checks address-dependent code against one memory layout, where every object is aligned to a large power of two (2^52 bytes with 12 object bits), and objects sit in a fixed order.

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

Kani 0.68.0, with its default settings, reports both as VERIFICATION SUCCESSFUL. ESBMC, reading the GOTO binaries Kani built for them, reports both as VERIFICATION FAILED, each with a counterexample.

CBMC has no option that leaves addresses open. Changing the flag value does not help either. More object bits shrink the alignment, to 2^(64-k) bytes with k bits, but the order stays fixed and the alignment stays at least 2^12 bytes for any k that leaves room for offsets. Fewer bits run out of objects: CBMC's default of 8 object bits allows only 256, and on the 85 harnesses ESBMC cannot decide, CBMC stops with "too many addressed objects" on 56 of them. The standard library has real code of this kind, such as `align_offset` and the alignment checks in `ptr` and `slice`. Among the 1,792 harnesses ESBMC decides, it agrees with Kani on every one, so the difference exposed no wrong proof in the library; we cannot say the same for the 96 it does not decide.

## What we learned

The part that costs time can be the right part. Most of ESBMC's timeouts come from an address model that refuses to assume a layout, and that same model catches the address bugs Kani's layout hides. Copying CBMC's encoding would buy speed and lose that.

Having different tools checking the same benchmarks can only increase trustworthiness. Both CBMC and ESBMC use complementary techniques, and many design choices can lead to what this post noticed.


## References

<style>ul.bibliography{list-style:none;padding-left:0}ul.bibliography li{margin-bottom:.6em}</style>

{% bibliography --file papers --file blog --cited_in_order --style ieee --template bib_numbered --group_by none --bibliography_list_tag ul %}
