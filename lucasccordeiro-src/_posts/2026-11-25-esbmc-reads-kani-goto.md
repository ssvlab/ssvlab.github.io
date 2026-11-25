---
layout: post
title: "ESBMC reads Kani's GOTO: a second engine for Rust standard-library proofs"
date: 2026-11-25
author: Lucas C. Cordeiro and Rafael Sá Menezes
description: ESBMC now verifies the CBMC GOTO binaries that Kani generates for the Rust proof harnesses, with no conversion step in between. We explain what's changed, why it's important to be reading the binary directly and what a sweep over all 1,888 verify-rust-std harnesses does and doesn't show.
tags: [formal-verification, esbmc, rust, kani]
categories: [research]
related_posts: false
---

Safe Rust eliminates data races, dangling references and out of bounds accesses, provided the `unsafe` code beneath it plays its part. A fair bit of that `unsafe` code is in the standard library. `Vec`, `String`, `slice`, `NonNull` and the integer types all wrap raw pointer arithmetic, uninitialised memory and compiler intrinsics up with safe APIs and every Rust program assumes those wrappers are correct. A single missing bounds check in `core` is a bug in every program that uses it.

The [Verifying the Rust Standard Library](https://github.com/model-checking/verify-rust-std) challenge (run by AWS with the support of the Rust Foundation) takes that trust and turns it into proof obligations {% cite cook2026verifying --file blog --style ieee %}. The repo is a fork of the Rust library with verification harnesses side by side with the code under scrutiny and CI runs all the approved tools on every PR. ESBMC {% cite dantas2026esbmc --style ieee %} is one of the five tools listed in the README as accepted (along with Kani, Flux, KMIR and VeriFast). ESBMC doesn't parse Rust at all. It verifies the same harnesses that Kani does, by reading the CBMC GOTO binaries that Kani produces.

This is all about the change that made that route viable. Prior to this year there was a separate program ([goto-transcoder](https://github.com/esbmc/goto-transcoder)) that would take Kani's output and convert it into ESBMC's own GOTO format. Since [ESBMC v8.4](https://github.com/esbmc/esbmc/releases/tag/v8.4) we've had `esbmc --binary` which can read Kani's CBMC binaries directly. The CI for the challenge stopped invoking the transcoder in October ([verify-rust-std#710](https://github.com/model-checking/verify-rust-std/pull/710)) and removed the name last week ([#779](https://github.com/model-checking/verify-rust-std/pull/779)). On a sweep of all 1,888 harnesses in the repo, the ESBMC master branch now agrees with Kani on 1,784 of them (94.5%) with zero false alarms and zero missed bugs, at 900s and 15 GB per harness. The rest of this post goes into how we got there, what that figure actually means and what it doesn't.

<img src="{{ '/assets/img/blog/2026-11-25-esbmc-kani-pipeline.svg' | relative_url }}" alt="Pipeline from a Rust harness through kani-compiler to a CBMC GOTO binary, harness.out. Three routes leave the binary: Kani's own back end (goto-instrument and CBMC), the old ESBMC route through goto-transcoder and library.goto (dashed), and the current route, esbmc --binary, which reads the binary in process." style="width:100%;height:auto;background:#fff;padding:8px;border-radius:4px">

*Figure 1. Kani compiles each harness down to a CBMC GOTO binary. CBMC is Kani's own back end. ESBMC used to require the goto-transcoder in between (dashed) but since v8.4 it just reads the binary itself.*

## A harness from the standard library

Here's one of the harnesses that the challenge's ESBMC job checks. The integer types in `core` have `unchecked_mul` which will multiply without any overflow check and is undefined behavior if the result overflows. A `requires` clause is provided to indicate when a call is safe (`library/core/src/num/int_macros.rs`):

```rust
#[requires(!self.overflowing_mul(rhs).1)]
pub const unsafe fn unchecked_mul(self, rhs: Self) -> Self {
```

and a macro in `library/core/src/num/mod.rs` generates one harness per integer type:

```rust
#[kani::proof_for_contract($type::$method)]
pub fn $harness_name() {
    let num1: $type = kani::any::<$type>();
    let num2: $type = kani::any::<$type>();
    unsafe {
        num1.$method(num2);
    }
}
```

`kani::any` makes both operands nondeterministic so the harness covers every pair of values. `proof_for_contract` tells Kani to assume the `requires` clause and then check that the body doesn't panic, doesn't have any arithmetic overflow and doesn't have any undefined behavior that Kani models. The 1,888 harnesses in the repo are all of this form: 1,236 are contract harnesses of this type and 652 are plain `#[kani::proof]` harnesses.

## Where Kani's work ends and a back end begins

Kani is a Rust model checker built on top of CBMC. It has its own compiler (`kani-compiler`) which hooks into `rustc`, takes the program after it's been lowered to MIR (rustc's mid-level IR) and translates that into a GOTO program (CBMC's intermediate language of assignments, guarded jumps, function calls, assumptions and assertions). Kani then runs `goto-instrument` and CBMC on that program and interprets the report that CBMC produces.

Every Rust-specific decision (the layout of an enum, where each overflow check goes etc) has been made by the time the GOTO binary is written. The back end just has to answer the question "can any assertion fail?" That's where ESBMC comes in. Kani with `--keep-temps --only-codegen` stops after codegen and produces one `.out` file per harness. A second engine that reads those files inherits Kani's Rust semantics and then adds its own search. ESBMC encodes the program into SMT (Bitwuzla is the default solver) rather than SAT and offers k-induction and incremental BMC on top of plain bounded model checking. If two engines disagree on the same binary then one of them has a bug and the binary is a ready made reproducer.

## The first integration: translate, then verify

One of us (Rafael) built the first bridge in 2024. goto-transcoder is a Rust program which takes a CBMC GOTO binary and outputs the same program in ESBMC's GOTO format. The two formats are quite distant from each other despite sharing a common ancestry (ESBMC was originally a fork of CBMC). The encoding of a number is different too: CBMC writes varint words (7 bits per byte) and ESBMC writes big-endian 32-bit words. In Jan 2025 the challenge's CI started off running ESBMC via the transcoder on the `checked_unchecked_*` contracts ([verify-rust-std#236](https://github.com/model-checking/verify-rust-std/pull/236)). The job would take each `.out`, link it to a prebuilt `library.goto` with ESBMC's C library and entry point and then run ESBMC on the result.

It worked, but it introduced a third program between Kani and the verdict with its own release cycle. Kani's output changes as Kani evolves and every change had to be picked up by the transcoder and ESBMC in turn. By October 2026 that coupling had broken with ESBMC 7.10 segfaulting on the transcoder's output for every contract built by Kani `main` ([verify-rust-std#710](https://github.com/model-checking/verify-rust-std/pull/710)).

## Reading the binary in ESBMC

The direct reader arrived as [esbmc#5291](https://github.com/esbmc/esbmc/pull/5291) in June 2026 and shipped with v8.4. It's essentially the same design as the transcoder, just running inside ESBMC.

1. `goto_binary_reader` looks at the magic bytes. `0x7f 'G' 'B' 'F'` takes you down the CBMC path, plain `GBF` is the native one.
2. `read_cbmc_goto_object.cpp` deals with decoding the varint stream, the shared string and shared subtree references and the symbol and function tables. It supports format version 6.
3. `cbmc_adapter.cpp` takes CBMC's expressions and type conventions and converts them into ESBMC's, renumbers the jump targets and resolves the struct tags.
4. ESBMC compiles a minimal boilerplate C file via its own front-end to produce what the `library.goto` used to supply (the C library models and the `__ESBMC_main` entry wrapper) and then links it in the same process.
5. The entry wrapper is pointed at CBMC's `__CPROVER__start` or at the harness named by `--function`.

From there it goes through ESBMC's normal pipeline: GOTO processing, symbolic execution, SMT encoding, solving. The hello world harness from Kani's tutorial runs as:

```
esbmc --binary test__RNvCsjN3sjT3oKaE_4test4main.out --function _RNvCsjN3sjT3oKaE_4test4main
```

and ESBMC prints `CBMC goto-binary detected: linking ESBMC additions automatically` prior to it starting. No `library.goto` is involved.

## Why reading the binary directly matters

Removing a conversion step sounds like plumbing. The engineering record of the reader is quite clear on this point: the difficult bit about consuming another tool's intermediate language is the meaning of the program, the bytes are the easy bit. A reader that correctly decodes every byte can still give the wrong answer and indeed several of the early bugs did just that.

- **Instruction kinds.** ESBMC and CBMC number their GOTO instruction kinds identically up to 18 and then diverge at 19 (CBMC has `INCOMPLETE_GOTO`, ESBMC has `THROW_DECL`). [esbmc#5717](https://github.com/esbmc/esbmc/pull/5717) replaced the implicit numeric match with an explicit table and rejects the kinds that ESBMC models differently (`START_THREAD`, `END_THREAD`) with a named diagnostic.
- **Entry point.** Prior to [esbmc#5719](https://github.com/esbmc/esbmc/pull/5719) the synthesized `__ESBMC_main` would have called the boilerplate's empty `main` rather than the harness. ESBMC would verify an empty program and could therefore report `VERIFICATION SUCCESSFUL` on a harness whose assertion does in fact fail.
- **Memory predicates.** CBMC's `__CPROVER_r_ok`, `w_ok` and `rw_ok` were initially set to constant `true`, so ESBMC proved `__CPROVER_r_ok(malloc(8), 16)`, which CBMC of course refutes. [esbmc#7411](https://github.com/esbmc/esbmc/pull/7411) gave them a proper encoding.
- **Wide constants.** The adapter was padding out every converted constant to 32 bits in exactly the same way as the reference converter did, so `x == -5000000000LL` would read `x` as a positive 32 bit value and ESBMC would report a false `FAILED`. [esbmc#5916](https://github.com/esbmc/esbmc/pull/5916) made the conversion respect the width of the constant.

That last bug was part of the port. The transcoder had it too. Moving the reader into ESBMC meant that every such convention was now right next to the code that depended on it, with a fix and a regression test landing in the same pull request. The `regression/goto-transcoder` directory in ESBMC (despite the name) now contains 385 tests that all load a CBMC binary. At least 60 of those are Kani written.

The second reason is information that a converter is likely to lose. CBMC attaches a property class to each assertion, `goto-cc` and Kani write loop invariants on the loop back edges, and Kani's helper functions all have the `__KANI_` prefix. A reader inside ESBMC sees all of that and can act on it. The converter has to pass all that information through to the second format and each one it loses is going to change what ESBMC is asked to verify.

## Making ESBMC behave like a Kani back end

Reading the binary is necessary but not sufficient. Kani's driver does the interpretation of CBMC's raw output and ESBMC has to do the same interpretation in order to give the same answer. Most of the work this autumn was down in that area.

**Reachability and cover checks.** Kani inserts assertions which are intended to fail. A `reachability_check` fails if its location is reachable and a `cover` fails if its condition can be satisfied. Kani treats both as information rather than as bugs. After the [kani#5093](https://github.com/model-checking/kani/pull/5093) change every contract harness had one and every contract failed under ESBMC ([esbmc#10875](https://github.com/esbmc/esbmc/issues/10875)). ESBMC v8.6 added `--ignore-property-class` which removes those assertions and [esbmc#10877](https://github.com/esbmc/esbmc/pull/10877) added `--report-property-class` which omits them from the verdict and just reports them afterwards as REACHABLE, UNREACHABLE, SATISFIED or UNSATISFIABLE.

**Kani's assumptions.** Kani runs CBMC with `--no-malloc-may-fail`. ESBMC's default is to allow `malloc` to return `NULL` which gave us two false alarms (`check_vecdeque_swap` and `verify_swap_remove`). Since [esbmc#10975](https://github.com/esbmc/esbmc/pull/10975), if ESBMC sees a symbol called `__KANI_...` in a CBMC binary it assumes `malloc` and `realloc` both succeed. [esbmc#10902](https://github.com/esbmc/esbmc/pull/10902) likewise stopped ESBMC from adding an alignment check that CBMC doesn't make, which was the reason Kani's unaligned-load harnesses were failing.

**A default strategy.** Lots of harnesses have loops with no unwinding bound. Plain BMC just keeps unrolling them and in our very first full sweep 134 harnesses ran out of memory that way. [esbmc#10942](https://github.com/esbmc/esbmc/pull/10942) by default has ESBMC verify a Kani binary with `--k-induction --unlimited-k-steps --max-inductive-step 3` unless a strategy or bound is specified on the command line. We ran the four strategies on the same 1,888 harnesses in the first instance (master `4757f8a6bd`, 900s, 15 GB): plain BMC agreed with Kani on 1,690, k-induction on 1,716, incremental BMC on 1,707 and IC3/PDR (`--ts-pdr`) on 1,700. PDR reported 7 harnesses as safe that Kani expects to be unsafe. k-induction had the most agreements and reported none of those harnesses as safe so it became the default.

**Pointer and memory modeling.** The rest is just standard model checker work. Rust's `core` exercises the model checker a lot harder than most C code really does: pointers through unions and byte-level reinterprets ([esbmc#10948](https://github.com/esbmc/esbmc/pull/10948), [#10969](https://github.com/esbmc/esbmc/pull/10969), [#11012](https://github.com/esbmc/esbmc/pull/11012)), `r_ok` ranges near 2<sup>63</sup> ([#10943](https://github.com/esbmc/esbmc/pull/10943)) and objects that absolutely must not cross 2<sup>63</sup> ([#10922](https://github.com/esbmc/esbmc/pull/10922)). One of the issues in that area actually demonstrates the value of a second engine. Three false alarms in the sweep (`check_bytes`, `check_invariant`, `check_u64_fmt`) all traced back to [esbmc#10965](https://github.com/esbmc/esbmc/issues/10965). When symbolic execution can't propagate a struct member then a copy of the struct will have a read of its source and the copy's pointer will then follow the source's later value. On a 15 line C program that same defect leads to a false proof which CBMC refutes on the same binary. [esbmc#10969](https://github.com/esbmc/esbmc/pull/10969) fixed both.

## ESBMC in the challenge's CI

The challenge runs ESBMC in its own workflow ([`esbmc.yml`](https://github.com/model-checking/verify-rust-std/blob/main/.github/workflows/esbmc.yml)). It has two steps: `scripts/run-kani.sh --kani-args --keep-temps --only-codegen` to build the GOTO binaries and [`scripts/run-esbmc.sh`](https://github.com/model-checking/verify-rust-std/blob/main/scripts/run-esbmc.sh) which downloads a pinned ESBMC release and then runs it for each of the selected harnesses.

```
esbmc --binary <harness>.out --function <harness> \
    --ignore-property-class reachability_check --ignore-property-class cover
```

[verify-rust-std#710](https://github.com/model-checking/verify-rust-std/pull/710) switched to the direct reader in October. [#779](https://github.com/model-checking/verify-rust-std/pull/779) (merged 20th November) pinned v8.7, added the property class options and renamed the workflow, script and documentation from goto-transcoder to ESBMC.

What the CI actually checks is very narrow. The workflow picks up `checked_unchecked.*.out` which today matches four contracts (`unchecked_mul` for `i8`, `u8`, `i16` and `u16`). On the last run on `main` (Nov 21 ESBMC 8.7.0, Bitwuzla 0.9.0) all four reported `VERIFICATION SUCCESSFUL`. That's the full extent of the ESBMC results in the CI challenge. A PR to move the job to v8.8 (which has the k-induction and `malloc` defaults) is open ([verify-rust-std#789](https://github.com/model-checking/verify-rust-std/pull/789)).

## Measuring the whole repository

To get a sense of just how far the route goes beyond those four contracts we ran ESBMC on every harness in the repository (outside of the challenge CI). The setup was:

- **Harnesses:** all 1,888 in verify-rust-std at the merge of [#766](https://github.com/model-checking/verify-rust-std/pull/766), compiled by the Kani commit that the CI pins to (`53cb531`). For 1,772 of them Kani expects a success, for the other 116 Kani expects a failing check (e.g. the harness is marked `should_panic`).
- **Reference:** Kani's own CI run on the same commit confirms all 1,888 as expected. "Agree" means ESBMC's verdict matches Kani's expectation. A *false alarm* is a `FAILED` when Kani expects it to succeed. A *missed bug* is a `SUCCESSFUL` when Kani expects it to fail.
- **Limits:** 900s and 15GB per harness, one core, under BenchExec on an AWS r7a.16xlarge instance, ESBMC built from master.

| ESBMC | Configuration | Agree (n = 1,888) | False alarm | Missed bug | Timeout | Out of memory |
|---|---|---|---|---|---|---|
| master `4757f8a6bd` | plain BMC | 1,690 (89.5%) | 12 | 0 | 52 | 134 |
| master `03233ba208` | default for Kani binaries (k-induction) | 1,784 (94.5%) | 0 | 0 | 103 | 1 |
| master `03233ba208` | default plus `--loop-invariant` | 1,780 (94.3%) | 0 | 0 | 106 | 0 |
| master `03233ba208` | `--parallel-solving --multi-property`, harness bounds as `--unwindset`, 4 cores | 1,745 (92.4%) | 0 | 0 | 30 | 113 |

Row 1 is from 22nd Nov, the other three from 24th Nov. In the default config the 23 harnesses that have a `#[kani::unwind]` bound are all running with that bound under plain BMC (a bound on the command line turns off the k-induction default). There are two `UNKNOWN`s to complete the `--loop-invariant` row. For an earlier reference point we reported last week that ESBMC v8.7, under much tighter constraints of 60s and 4 GB, agreed with Kani on 79.3% of the same 1,888 harnesses (the rest were using CBMC GOTO features that v8.7 didn't support). Those constraints are very different from those in the table so the figure is not directly comparable.

Three readings follow from the table and one claim doesn't.

**Wrong answers are extremely rare and none remain in this corpus.** No config on `03233ba208` has a false alarm or a missed bug and none of the twelve harnesses that false-alarmed under plain BMC on `4757f8a6bd` still do. The fixes described above (including #10969) are in between the two commits.

**What's left is cost, not unsupported features.** In the default configuration every one of the 1,888 binaries loads and every harness ESBMC doesn't decide stopped at a resource limit (103 timeouts, one memory out). Kani doesn't have that problem on those harnesses. On the challenge CI runners Kani's CBMC verifies all 103 with a median of 8.7s and a max of 293s (`non_null_check_write_unaligned_u128`). The machines are different so the comparison is just indicative but the direction is clear: on those harnesses CBMC's SAT encoding is faster than ESBMC's current encoding.

**Spending more cores on the parallel solving didn't help at all** -- parallel solving still didn't recover any harnesses. In fact 73 of the former timeouts and 39 harnesses that had agreed just ran out of memory instead. That's consistent with the way that option was keeping one solver per claim alive at once. Master has now bounded it with a worker pool ([esbmc#11047](https://github.com/esbmc/esbmc/pull/11047)) and we're re-running that config to see the effect.

What the table doesn't show is that ESBMC finds bugs that Kani misses. All the harnesses in the repository already pass under Kani so this is a measure of how much of Kani's ground the second engine covers and how often the two engines disagree. It's a per harness comparison rather than a per property comparison and it's using ESBMC's master branch rather than a release. v8.8 has the k-induction and `malloc` defaults in it but not #10969 or #11012.

## A harder case: float-to-decimal conversion

By construction every harness in the repo is one that Kani can finish. Challenge 28 (safety proofs for the float-to-decimal code in `core::num::flt2dec`) is a better test of what a second engine might be able to contribute. The harnesses so far have either stubbed or assumed away the arithmetic in the Grisu and Dragon digit loops. We did write [a plan](https://github.com/esbmc/esbmc/blob/master/docs/roadmap/verify-rust-std-challenge-28-plan.md) to run the unstubbed loops through ESBMC and set a gate for it: the unstubbed Grisu harnesses had to be in budget.

They didn't. On ESBMC v8.8, not a single unstubbed Grisu harness completed, even at 3600s (four times the sweep budget). Splitting the f64 shortest mode harness into one run per claim (900s each, with `round_and_weed`'s loop bounded at 10) managed 100 of the 111 claims (including all of the `Fp::mul` overflow checks and the digit bound `q < 10` that the submitted solutions assume). The 11 that timed out are the `buf[i]` index check, one comparison and nine of the overflow checks on the error bounded arithmetic in the digit loop. We recorded that as a failed gate. In the process it led to a model of `memset` with a symbolic offset or length ([esbmc#11018](https://github.com/esbmc/esbmc/pull/11018)) and the per-claim results reduce the open part of the problem to just a handful of claims which would require loop invariants.

## What ESBMC does not support yet

These are different categories and to mix them would be to misrepresent where ESBMC actually stands.

**CBMC and Kani GOTO features ESBMC does not handle.** Reader accepts GOTO format version 6 only. It declines (with an error rather than a wrong verdict) SIMD operations, `setjmp`, `va_start` and `__CPROVER_DYNAMIC_OBJECT` as well as `__CPROVER_havoc_object` on a pointer value and `__CPROVER_array_set` on arrays that are not whole objects. For contracts `is_fresh` allocates and writes through but does not check separation between pointers. All of these are from the [CPROVER support roadmap](https://github.com/esbmc/esbmc/blob/master/docs/roadmap/cprover-support-roadmap.md) (last reviewed October 1) and none of them appear in the default sweep above.

**Loop and frame contracts.** [esbmc#11017](https://github.com/esbmc/esbmc/pull/11017) applies the loop invariants that `goto-cc` and Kani store in the binary (via `--loop-invariant` and related options). It has no effect on Kani at this stage: Kani simply lowers `#[kani::loop_invariant(...)]` to a call of a generated closure and the reader will ignore any invariant that has a side effect. That will impact all 13 verify-rust-std harnesses that have a loop contract ([esbmc#11051](https://github.com/esbmc/esbmc/issues/11051), open). ESBMC also never sees any `modifies` clauses as `--only-codegen` stops before `goto-instrument`, the step that turns them into checks.

**Options which don't work on Kani binaries.** With `--ir` (unbounded integers) ESBMC aborts on Kani binaries which do a struct to integer cast (which `NonNull::dangling()` does) ([esbmc#11023](https://github.com/esbmc/esbmc/issues/11023), open). The default bit-vector encoding works with the same binaries.

**Resource limits.** The 104 harnesses without a verdict in the default sweep ran out of time or memory. One known culprit is `memcpy` with a symbolic length at a symbolic offset which still falls back to a byte loop that unwinds to the bound ([esbmc#11026](https://github.com/esbmc/esbmc/issues/11026), open).

## What comes next

- **Run more of the repo in the challenge's CI.** The job currently checks four contracts with v8.7. The first step is to move to v8.8 (#789) but the one that actually makes a difference is to broaden the scope beyond `checked_unchecked`.
- **Close 104.** Profile the timeouts by module (starting with the symbolic `memcpy` and the `non_null_check_*_unaligned` family) and see if #11047 brings back the harnesses that `--parallel-solving` lost due to memory.
- **Kani loop contracts.** Evaluate the closure call where the invariant is checked (#11051) so that `--loop-invariant` gets to the 13 harnesses that carry one.
- **Compare per property.** Agreement on a verdict can hide disagreement on individual checks. `--multi-property` with `--report-property-class` gives the per-check report needed to compare against Kani claim by claim.

Reading the binary directly changes what ESBMC can be in this ecosystem. Before, it was a tool that verified a translation of Kani's output, and the translation could break with any Kani release. Now it reads the same binary CBMC reads, applies the same assumptions Kani makes, and runs a different solver stack and different proof strategies over it. On the 1,888 harnesses we measured, that second engine agrees with the first on 94.5% and never contradicts it. Where the two part ways, a disagreement points to a bug in one of them and comes with a binary that reproduces it. The open question is whether ESBMC can prove harnesses Kani cannot. Challenge 28 says not yet, for unstubbed Grisu, and the per-claim results there show where to look next.

## Join us

We are looking for PhD students, postdocs and collaborators interested in Rust verification, model checking and SMT. ESBMC is open source, and the CBMC reader, its 385 regression tests and the roadmap documents are in [ESBMC master](https://github.com/esbmc/esbmc). If this interests you, email [Lucas Cordeiro](mailto:lucas.cordeiro@manchester.ac.uk) with a short note on what you would like to work on, or talk to the group first on our public [Zulip chat](https://systemsandsoftwaresecurity.zulipchat.com/join/6ajabxaurkcwl6tl3ify55jv/).

## References

<style>ul.bibliography{list-style:none;padding-left:0}ul.bibliography li{margin-bottom:.6em}</style>

{% bibliography --file papers --file blog --cited_in_order --style ieee --template bib_numbered --group_by none --bibliography_list_tag ul %}
