# ECPS Verification Tutorial

This repository supports the **Specification and Verification of Embedded and Cyber-Physical Systems (ECPS)** tutorial using [ESBMC](https://github.com/esbmc/esbmc).

## 🔧 Setup

Build ESBMC rom source. See [BUILDING]([setup/install_esbmc.md](https://github.com/esbmc/esbmc)).

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

## 🚀 Run an Example

```bash
esbmc examples/assert_example.c

