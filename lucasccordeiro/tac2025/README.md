# ECPS Verification Tutorial

This repository supports the **Specification and Verification of Embedded and Cyber-Physical Systems (ECPS)** tutorial using [ESBMC](https://github.com/esbmc/esbmc).

## 🔧 Setup

Build ESBMC from source. See [BUILDING](https://github.com/esbmc/esbmc).

You can also download the binary. See [RELEASES](https://github.com/esbmc/esbmc/releases)


## 🧪 Topics Covered

- Formal Specification with Temporal Logic (LTL)
- Safety & Liveness Verification using ESBMC
- ECPS Modeling Exercises
- LLM-Generated Code + Formal Verification

## 📂 Folder Structure

- `examples/`: Basic verification examples
- `exercises/`: Hands-on ECPS modeling tasks
- `ai_generated/`: Code generated using LLMs (e.g., ChatGPT, Copilot)
- `slides/`: Presentation slides for the tutorial

## 📌 Requirements

- Linux Ubuntu
- GCC/Clang
- [ESBMC](https://github.com/esbmc/esbmc)
- [ltl2ba](https://github.com/esbmc/libltl2ba)

## 🚀 Run an Example

```bash
esbmc examples/assert_example.c
````

Expected output:

````
ESBMC version 7.9.0 64-bit x86_64 linux
Target: 64-bit little-endian x86_64-unknown-linux with esbmclibc
Parsing examples/assert_example.c
Converting
Generating GOTO Program
GOTO program creation time: 0.444s
GOTO program processing time: 0.002s
Starting Bounded Model Checking
Symex completed in: 0.002s (13 assignments)
Slicing time: 0.000s (removed 11 assignments)
Generated 1 VCC(s), 1 remaining after simplification (2 assignments)
No solver specified; defaulting to Boolector
Encoding remaining VCC(s) using bit-vector/floating-point arithmetic
Encoding to solver time: 0.000s
Solving with solver Boolector 3.2.2
Runtime decision procedure: 0.000s
Building error trace

[Counterexample]


State 1 file examples/assert_example.c line 3 column 3 function main thread 0
----------------------------------------------------
Violated property:
  file examples/assert_example.c line 3 column 3 function main
  x must be greater than 10
  x > 10


VERIFICATION FAILED
````

