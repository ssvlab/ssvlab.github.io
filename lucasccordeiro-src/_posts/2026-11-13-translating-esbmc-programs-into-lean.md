---
layout: post
title: "Translating ESBMC programs into Lean: what a second prover adds"
date: 2026-11-13
author: Lucas C. Cordeiro and Rafael Sá Menezes
description: ESBMC can now translate its GOTO programs into Lean 4. We ran both provers on the same programs to see where each one is stronger, what ESBMC can learn from Lean's proofs, and what a disagreement between them tells us.
tags: [formal-verification, esbmc, lean]
categories: [research]
related_posts: false
mermaid:
  enabled: true
  zoomable: false
---

A model checker reports one of three verdicts: safe, unsafe or unknown. ESBMC prints them as `VERIFICATION SUCCESSFUL`, `VERIFICATION FAILED` and `VERIFICATION UNKNOWN`. An unsafe verdict is easy to validate, because it comes with a counterexample that can be replayed against the program. A safe verdict is harder. It is the output of a parser, a symbolic execution engine, a simplifier, an SMT encoding and a solver working in sequence, and a defect in any of them can make an incorrect program look safe. Our [last post](https://ssvlab.github.io/lucasccordeiro/blog/2026/llms-propose-verifiers-check/) ended by asking who checks the checker. One way to answer is to give the same program to a second prover that works differently and see whether the two agree.

[ESBMC](https://github.com/esbmc/esbmc) is the SMT-based model checker that we develop {% cite dantas2026esbmc --style ieee %}. Its front ends for C, C++, Python, Solidity and ladder diagrams all produce the same intermediate language, the GOTO program. A new option, `--goto2lean`, prints that program as [Lean 4](https://lean-lang.org/) definitions, together with a theorem stating that no assertion fails. Lean is a proof assistant: a proof counts only once Lean's kernel, a small checker, has accepted it. So far the translator handles Booleans and integers, `if`/`else`, loops (one at a time), calls to non-recursive functions, and quantifiers in assertions. It rejects arrays and pointers.

The two provers can work together in more than one way. When ESBMC cannot finish a proof, Lean sometimes can, and Lean's proof then shows which reasoning steps ESBMC was missing; we wrote some of those steps back into the C program and ESBMC finished. If the two disagree on a program, at least one of them has a bug, which is the check our last post asked for. We show both, the second with a real ESBMC bug.

```mermaid
flowchart LR
    S["Source<br/>C, C++ or Python"] --> G["GOTO program<br/>ESBMC front end"]
    G --> E{"ESBMC<br/>symbolic execution,<br/>SMT solver"}
    G --> T["--goto2lean<br/>weakest precondition<br/>in Lean 4"]
    T --> L{"Lean 4<br/>bv_decide, omega, grind<br/>or a supplied proof"}
    E --> V1["Verdict<br/>and counterexample"]
    L --> V2["Theorem proved<br/>or refuted"]
    V1 --> C["Compare"]
    V2 --> C
```

*Figure 1. Two routes from the same GOTO program. Both start after the front end, so a front-end bug is invisible to both.*

Note that all results below were measured on a laptop, with ESBMC's development version and Lean 4.35.0.

## A loop that ESBMC cannot finish

Our first example is a loop that adds up the first `n` cubes and the first `n` whole numbers, then asserts [Nicomachus's theorem](https://en.wikipedia.org/wiki/Squared_triangular_number): the sum of the cubes equals the square of the sum. For `n = 4`, 0 + 1 + 8 + 27 = 36 = (0 + 1 + 2 + 3)<sup>2</sup>.

```c
unsigned nondet_uint(void);
int main(void) {
  unsigned n = nondet_uint();
  unsigned s = 0, c = 0, i = 0;
  while (i < n) {
    s = s + i;
    c = c + i * i * i;
    i = i + 1;
  }
  __ESBMC_assert(c == s * s, "Nicomachus");
  return 0;
}
```

The program uses 32-bit `unsigned` arithmetic, so large values wrap around. Nicomachus's theorem survives that. It is an equation built from additions and multiplications, both sides wrap in the same way, and the assertion holds for every `n`.

Proving something about a loop for every `n` needs a loop invariant: a fact that is true before the loop and stays true after each iteration. ESBMC does not find one here by itself, and plain k-induction answers `VERIFICATION UNKNOWN`. So we supplied one with `__ESBMC_loop_invariant`: `2 * s == i * (i - 1)`, `c == s * s` and `i <= n`. The hard part is the middle fact. ESBMC has to show that if `c` equals `s * s` before an iteration, then `c + i * i * i` equals `(s + i) * (s + i)` after it. It passes that question to an SMT solver, which handles 32-bit arithmetic by turning every multiplication into a circuit of logic gates and searching the circuit for a counterexample. Cubing a 32-bit number gives a large circuit. Neither of the two solvers we tried, Z3 and Bitwuzla, answered within five minutes.

`esbmc ucubes.c --goto2lean` produces this Lean file instead:

```lean
def main_loop1 (n : BitVec 32) (s : BitVec 32) (c : BitVec 32) (i : BitVec 32)
    (post : BitVec 32 → BitVec 32 → BitVec 32 → BitVec 32 → Prop)
    (ret : BitVec 32 → Prop) : Prop :=
  (¬(i < n) →
    post n s c i) ∧
  ((i < n) →
  let s := (s + i);
  let c := (c + ((i * i) * i));
  let i := (i + (1#32));
  main_loop1 n s c i post ret)
coinductive_fixpoint

def main (post : BitVec 32 → Prop) : Prop :=
  ∀ n : BitVec 32,
  let s := (0#32);
  let c := (0#32);
  let i := (0#32);
  main_loop1 n s c i (fun (n : BitVec 32) (s : BitVec 32) (c : BitVec 32) (i : BitVec 32) =>
    -- Nicomachus
    (c = (s * s)) ∧ (
    post (0#32))) post

theorem main_safe : Prog.main (fun _ => True) := by
  -- Not closed automatically: each loop needs an invariant (apply Prog.<loop>.coinduct).
  sorry
```

*Listing 1. The Lean that `--goto2lean` generates for the loop, with the namespace and one renaming line removed. `sorry` is Lean's placeholder for a missing proof.*

Listing 1 is the inductive version of the program. The `while` loop is gone; in its place is `main_loop1`, a definition that refers to itself. Read it as a statement about one visit to the loop head with the current values of `n`, `s`, `c` and `i`. If `i < n` is false, the loop exits and the final check `c = s * s` must hold. Otherwise the body runs once, giving new values of `s`, `c` and `i`, and the same statement must hold again for those values, which is the self-reference. `main` makes the first visit, with `s`, `c` and `i` at zero and `n` arbitrary (the `∀`). The rest of the file follows one pattern: a nondeterministic value becomes `∀`, an `__ESBMC_assume` becomes `→`, and an assertion becomes `∧`. One keyword is new: `coinductive_fixpoint` allows the loop to run forever. A run that never exits never reaches the assertion, so the theorem only constrains runs that terminate.

From that definition Lean derives a proof rule, `Prog.main_loop1.coinduct`. To use it, you give a property of the loop variables. You then show that it holds at the first visit, and that whenever it holds at the loop head, the statement above holds with the property in place of the self-reference. That property is the loop invariant, and the rule is the loop-invariant rule of Hoare logic. Lean derives it from the definition, so the rule itself does not have to be trusted. Replacing `sorry` with the invariant we gave ESBMC completes the proof:

```lean
theorem main_safe : Prog.main (fun _ => True) := by
  simp only [Prog.main]
  intro n
  apply Prog.main_loop1.coinduct n _ _
    (fun s c i => 2#32 * s = i * (i - 1#32) ∧ c = s * s ∧ i ≤ n)
  · intro s c i ⟨hs, hc, hle⟩
    refine ⟨fun hlt => ⟨?_, trivial⟩, fun hlt => ⟨?_, ?_, ?_⟩⟩
    · have : i = n := by bv_omega
      subst this; exact hc
    · grind
    · grind
    · bv_omega
  · exact ⟨by decide, by decide, by bv_omega⟩
```

*Listing 2. The proof that replaces `sorry`. Lean checks it in 4.2 seconds.*

After the `apply ... coinduct` line, Lean asks for three things: the invariant holds before the loop, it survives one iteration, and on exit it implies the assertion. Most of the remaining lines are bookkeeping, and the two `grind` lines do the real work. `grind` is Lean's general-purpose automation, the hammer you try before writing a proof by hand. Part of what it does is algebra: it expands `(s + i) * (s + i)`, uses `2 * s = i * (i - 1)` to rewrite the result, and finds that both sides are the same polynomial, as you would on paper. It never builds a circuit, so the cube costs it no more than a sum. The gain comes from the algebra, not from Lean as such. When we replaced `grind` with `bv_decide`, the Lean tactic that does build a circuit and call a SAT solver, it timed out too.

## What ESBMC can learn from Lean's proof

Lean finished the proof, but ESBMC is the tool people run on their code, so we asked what Lean's proof could teach it. Listing 2 does three things that ESBMC's single query to the solver does not. It works on the start, the step and the exit as separate goals. At the exit it derives `i = n` from `i ≤ n` and `¬(i < n)` and substitutes it (the `have ... subst` line). And `grind` uses the invariant's equations as rewrite rules on the step. We tested each move by writing it back into the C program, and we also asked whether ESBMC could have supplied the invariant.

**Invariants.** ESBMC has an option, `--synthesise-loop-invariants`, that proposes invariants for loops whose counters and accumulators grow by a constant. On the counting loop from our demo (`s` and `i` both go up by one, and the program asserts `s == n` after the loop), it proposed `(i < n || i == n || i == 0) && (0 < n || i == 0) && s == i`. We pasted that predicate into the generated Lean file unchanged, and `bv_decide` proved the theorem in 9.5 seconds. On the Gauss and Nicomachus loops, the option reports that no loop matched its shape, because those accumulators grow by `i` and by `i * i * i`. So ESBMC can hand Lean the invariants of simple loops today. Polynomial invariants such as `2 * s == i * (i - 1)` still have to come from a person or a model.

**Hints.** Next we copied `grind`'s algebra into the loop body, as four `__ESBMC_assume` statements: the expansion of `(s + i) * (s + i)`, the regrouping of `2 * s * i`, the substitution of `i * (i - 1)` for `2 * s`, and the expansion of `i * (i - 1) * i + i * i`. Each holds for every 32-bit value. ESBMC proves the two expansions and the regrouping in under a second each, as separate programs. The substitution is congruence: equal values multiplied by the same `i` stay equal. The hints alone changed nothing, and neither solver answered in 300 seconds.

**Separate goals.** What made the difference was checking the claims one at a time. ESBMC normally sends all of a program's claims to the solver as one query; `--multi-property` sends each on its own, which is what Lean's `refine` does when it splits the proof into goals. With the hints and `--multi-property`, Z3 proves the 32-bit Nicomachus program in 6.0 seconds:

```c
unsigned nondet_uint(void);
int main(void) {
  unsigned n = nondet_uint();
  unsigned s = 0, c = 0, i = 0;
  __ESBMC_loop_invariant(2 * s == i * (i - 1) && c == s * s && i <= n);
  while (i < n) {
    __ESBMC_assume((s + i) * (s + i) == s * s + 2 * s * i + i * i);
    __ESBMC_assume(2 * s * i == (2 * s) * i);
    __ESBMC_assume(2 * s != i * (i - 1) || (2 * s) * i == (i * (i - 1)) * i);
    __ESBMC_assume(i * (i - 1) * i + i * i == i * i * i);
    s = s + i;
    c = c + i * i * i;
    i = i + 1;
  }
  __ESBMC_assert(c == s * s, "Nicomachus");
  return 0;
}
```

*Listing 3. The 32-bit Nicomachus program with `grind`'s steps written in. `esbmc --loop-invariant-check --multi-property --z3` reports `VERIFICATION SUCCESSFUL` in 6.0 seconds.*

Neither change is enough alone. Without the hints, `--multi-property` still times out, and so do the hints without it. Bitwuzla gives no verdict in any of these configurations. This is also what a hand proof in ESBMC looks like: the hints are assumptions, and the argument that they are true (three small lemmas and congruence) lives outside the program. ESBMC's `--loop-invariant-check` applies the invariant rule itself, so the start, the step and the exit no longer need separate programs tied together on paper.

**The exit.** The 32-bit Gauss loop, which keeps only `s` and asserts `2 * s == n * (n - 1)`, broke where we least expected it. With its invariant, both solvers stall on the exit claim: from `2 * s == i * (i - 1)`, `i <= n` and `!(i < n)`, conclude `2 * s == n * (n - 1)`. Written with `i == n` in place of the two inequalities, the same claim takes 0.46 seconds in both solvers. The solvers never derive the equality and substitute it. They compare two 32-bit multipliers bit by bit, and Lean's proof avoids that with one line. With `__ESBMC_assert(i == n, ...)` after the loop and `--multi-property`, Z3 proves the whole Gauss program in 0.57 seconds. Either change alone leaves it without a verdict.

Two of these moves could become ESBMC heuristics. The exit equality is cheap and local: when an invariant contains `i <= n` and the loop exits on `!(i < n)`, ESBMC can add `i == n` and substitute it before checking what follows. Solving the claims of an invariant separately is already an option and could be the default under `--loop-invariant-check`. The rewriting is harder. As a claim of its own, the identity behind `grind`'s step, (s + i)<sup>2</sup> − (c + i<sup>3</sup>) = (s<sup>2</sup> − c) + i·(2s − i(i − 1)), proves in 0.45 seconds in both solvers, but adding it as a fact to the step does not help. Bitwuzla's built-in abstraction of multiplication, which by default starts at 33 bits, did not help either when we lowered it to 32 bits on ESBMC's formulas. What the solvers lack is the use of an equation between products as a rewrite rule. That needs a pass in ESBMC that normalizes polynomials and substitutes the invariant's equations before the formula reaches the solver. We have not built it; Listing 3 does its job by hand.

## Catching a wrong verdict from ESBMC

The other use of a second prover is the one our last post asked for: catching ESBMC when it is wrong. A real test needs a real ESBMC bug, so we took one that ESBMC had until recently ([#10537](https://github.com/esbmc/esbmc/issues/10537), fixed in [#10576](https://github.com/esbmc/esbmc/pull/10576)) and replayed it on a build from 12 November, before the fix.

The bug involves `--ir`, which asks ESBMC to treat C integers as mathematical integers that never wrap. `--goto2lean` follows the same request and uses Lean's `Int`, so both routes are asked the same question. ESBMC's simplifier, the step that precomputes arithmetic on constants before the solver runs, ignored `--ir` and still wrapped constant results at 32 bits. Here is one of the regression tests from the issue:

```c
int nondet_int(void);
int main() {
  int x = nondet_int();
  __ESBMC_assume(x >= 0 && x <= 10);
  int y = x - 1 - 2147483647;
  __ESBMC_assert(y >= 0, "y >= 0");
  return 0;
}
```

Under `--ir`, `y` is at most −2147483638, so the assertion fails for every `x`. The old build says `VERIFICATION SUCCESSFUL`: an unsafe program reported as safe, the error this post began with. Lean's `Int` was the right model here. The translation did what `--ir` asked, and the wrong answer came from ESBMC.

Lean does not accept the translated theorem. Under `Int` its failure gives no concrete input, though: `omega` reports only that "a possible counterexample may satisfy the constraints 0 ≤ a ≤ 10". That range is still enough to settle the question without trusting Lean. We took `x = 0` from it and changed the assumption to `x == 0`. The old build then says `VERIFICATION FAILED`. A program that is safe for every `x` between 0 and 10 cannot be unsafe at `x = 0`, so ESBMC has contradicted itself, and the bug is in ESBMC. Running the old build again with `--no-simplify` gives `FAILED` for both versions, which points at the simplifier rather than the SMT encoding or the solver. Current master reports `FAILED` with `x = 0` and `y = -2147483648`, and Lean proves the negation of the theorem from that witness in four lines:

```lean
theorem main_unsafe : ¬ Prog.main (fun _ => True) := by
  intro h
  simp only [Prog.main] at h
  have := (h 0 (by omega)).1
  omega
```

The same replay does not work on every bug from that issue. In the test `y = ~b + INT_MIN`, the old build is wrong at `b = 0` as well, so fixing a point exposes nothing. `--goto2lean` also rejects `~` under `--ir`, so Lean has nothing to say. That is a real gap in the translator, but closing it needs care: the translation has to give `~` the same meaning as ESBMC's `--ir` mode, and ESBMC's own `--ir` encoding of `~` still wraps at 64 bits ([#10596](https://github.com/esbmc/esbmc/issues/10596)). Until that is settled, rejecting `~` is safer than picking a meaning.

## What each answer relies on

We do not trust Lean more than ESBMC across the board. ESBMC writes [verification witnesses](https://gitlab.com/sosy-lab/benchmarking/sv-witnesses) for violations and proofs, other teams' validators check them in [SV-COMP](https://sv-comp.sosy-lab.org/), and ESBMC can act as a witness validator itself. A validator re-verifies a witness with its own engine, though, so its whole pipeline is trusted in turn. Lean works differently. It is a term that Lean's kernel checks after the fact, independently of the tactic that built it, so a bug in `grind` or `omega` can make a proof fail but cannot make the kernel accept a false theorem (`bv_decide` is a partial exception, described below the table). The Lean route still relies on other parts, and the table lists them.

| Component | Shared by both routes? | Who checks it |
|---|---|---|
| Front end and GOTO conversion | Yes | Neither route; a front-end bug is invisible to both |
| Symbolic execution, simplifier, SMT encoding, solver | ESBMC only | The Lean route, by disagreeing |
| `--goto2lean` translator | Lean only | Trusted; it is not verified |
| `bv_decide` proofs | Lean only | Lean's kernel, plus compiled code that checks the SAT certificate |
| `omega`, `grind` and hand proofs | Lean only | Lean's kernel |

`#print axioms` on a theorem closed by `bv_decide` lists Lean's three standard axioms plus axioms named `_native.bv_decide`: the certificate checker runs as compiled code, so the trusted base includes Lean's compiler as well as its kernel. Proofs by `omega` and `grind` rely on the three standard axioms only.

The check is cheap on these programs. Over the medians of three runs on ten demo programs, translation took about 0.4 seconds for C and C++ and 1.2 seconds for Python (4.4 seconds for the Python program under `--ir`), and Lean checked each generated file in 1.5 to 1.7 seconds. Most of that is start-up of a Debug build; the numbers say nothing about scalability.

## Where each prover is stronger

We ran a handful of small programs through both routes. The verdicts and times are single runs.

| Program | ESBMC | Lean via `--goto2lean` |
|---|---|---|
| Midpoint `(lo + hi) / 2`, the overflow bug | `FAILED`, `lo = hi = 4294967295` | `bv_decide` refutes with the same values |
| `3*x + 5*y != 31` for `x`, `y` in 0..10, with `--ir` | `FAILED`, `x = 7`, `y = 2` | `omega` fails and prints a constraint over its internal `bmod_div_term` variables; in bit-vector mode `bv_decide` gives `x = 7`, `y = 2` |
| `x * x >= 0`, `--ir` | `SUCCESSFUL`, 0.46 s | `omega` and `grind` fail; 4-line case split |
| Gauss sum `2*s == n*(n-1)`, `--ir` | k-induction `UNKNOWN`; with the invariant, `SUCCESSFUL` in 0.47 s | same invariant plus `grind` |
| Nicomachus, `--ir` | k-induction `UNKNOWN`; with the invariant, `SUCCESSFUL` in 0.46 s; a wrong invariant is rejected | same invariant plus `grind` |
| Nicomachus, 32-bit | with the invariant, no verdict in 300 s from Z3 or Bitwuzla; with Listing 3, `SUCCESSFUL` in 6.0 s (Z3) | Listing 2, 4.2 s |
| Counting loop `s == n` | `SUCCESSFUL`, invariant synthesized | `bv_decide` with ESBMC's invariant, 9.5 s |
| Counting loop with the too-weak invariant `s == i` | `UNKNOWN`: "loop invariant too weak to prove this claim" | refuted, with the state `s = i = 4294967295`, `n = 2147483647` |
| An assertion with `__ESBMC_exists` | `SUCCESSFUL`, automatic | needs a 6-line proof that supplies the witness |
| Arrays, pointers | supported | rejected |

Which prover wins depends on how the program's numbers are modeled. With `--ir`, ESBMC treats integers as mathematical integers that never wrap, and Z3 proved the square, the Gauss sum and Nicomachus in under half a second each; Lean's integer tactic, `omega`, handles only linear arithmetic and proves none of them. Over 32-bit words the order reverses: `grind` proved Nicomachus from the invariant alone, and ESBMC needed Lean's steps written into the program. Running the 32-bit Nicomachus program with `--ir` does not move it to the easy side. Under `--ir`, ESBMC treats `unsigned` values as unbounded integers that can go negative, so the invariant `i <= n` fails at entry with a spurious `n = 4294967294` (really −2; we reported the misleading trace as [#10606](https://github.com/esbmc/esbmc/issues/10606)). With `__ESBMC_assume(n >= 0)` added, ESBMC proves the unbounded version in 0.40 seconds, but the 32-bit claim then follows only by a paper argument that ESBMC does not check.

ESBMC finds bugs and prints concrete inputs, handles the whole language, and for simple loops proposes the invariants that Lean needs. Lean asks for more human input, but a proof it accepts is checked by its kernel, and the steps of that proof are instructions ESBMC can follow. The 32-bit Nicomachus loop went from no verdict in either tool to a proof in both, and the ESBMC proof came from reading Lean's. That exchange is what we want to automate next.

## What comes next

- **Heuristics learned from Lean's proofs.** The exit equality and per-claim solving are small changes to ESBMC, and we plan to try them first. The larger one is the rewriting pass that Listing 3 does by hand: normalize polynomials and substitute the invariant's equations before the formula reaches the solver.
- **Invariants from ESBMC and from models.** ESBMC's synthesis covers loops that grow by a constant. The Nicomachus invariant is the kind of input we ask a language model to propose {% cite pirzada2024generated --style ieee %}, and when the SMT solvers stall on the step, Lean can still check the proposal.
- **Prove the translator.** The translator is the trusted link in the table above. Rafael's PhD thesis, [*GOTO: a verification framework for CProver tools*](https://ssvlab.github.io/lucasccordeiro/supervisions/phd_thesis_rafael.pdf) (University of Manchester, 2025), gives GOTO a formal semantics, mechanized in part in Isabelle, and treats unwinding, slicing and common-subexpression elimination as transformation passes over it. With that semantics in Lean, we can state the translator's correctness as a theorem: the weakest precondition that `--goto2lean` emits implies that no assertion fails in any execution allowed by the semantics. The same semantics lets us state what #10537 broke: a pass must preserve the meaning of the program under the selected encoding.
- **Arrays and pointers.** Most of the C code we verify uses them. They need a memory model in Lean that matches ESBMC's, and memory models are also outside the scope of the thesis's Isabelle formalization, so this work starts from the same gap.
- **A second route to Lean.** ESBMC can write its verification conditions as SMT-LIB 2 files, and [LeanWuzla](https://github.com/hargoniX/Leanwuzla) can check bit-vector problems of that kind with `bv_decide`. We have not yet run it on ESBMC's output. That route would check the solver's answer; `--goto2lean` checks the program.

## Join us

We are looking for PhD students, postdocs and collaborators interested in these problems: formal methods, program analysis and interactive theorem proving. ESBMC is open source, and the translator, its regression tests and its documentation are in [ESBMC master](https://github.com/esbmc/esbmc). If this interests you, email [Lucas Cordeiro](mailto:lucas.cordeiro@manchester.ac.uk) with a short note on what you would like to work on, or talk to the group first on our public [Zulip chat](https://systemsandsoftwaresecurity.zulipchat.com/join/6ajabxaurkcwl6tl3ify55jv/).

## References

<style>ul.bibliography{list-style:none;padding-left:0}ul.bibliography li{margin-bottom:.6em}</style>

{% bibliography --cited_in_order --style ieee --template bib_numbered --group_by none --bibliography_list_tag ul %}
