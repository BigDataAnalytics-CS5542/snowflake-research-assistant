# Lab 8 — Domain Adaptation

This directory contains the domain adaptation work from Lab 8, integrated into the main project for Project 3.

## Domain Task

The system was adapted for the **legal demand** domain — assisting with drafting, analyzing, and evaluating legal demand letters. Domain adaptation improves the model's ability to recognize legal claim patterns, structure demand letters, and produce actionable legal responses beyond what a general-purpose LLM provides.

## Contents

| Path | Description |
|------|-------------|
| `data/instruction_dataset.json` | 50 instruction-tuning examples across 5 task types |
| `training/qlora_finetune.ipynb` | QLoRA fine-tuning notebook (4-bit quantization, LoRA adapters) |
| `training/gepa_prompt_optimization2.ipynb` | GEPA-based prompt optimization for domain adaptation |
| `evaluation/eval_4_configs.ipynb` | Evaluation comparing 4 configurations (baseline, GEPA, QLoRA, combined) |
| `evaluation/evaluation_queries.md` | 10 evaluation queries used for benchmarking |
| `docs/dataset_notes.md` | Dataset construction notes and statistics |
| `LAB8_OVERVIEW.md` | Full lab specification and methodology |

## Instruction Dataset

50 examples covering 5 legal demand task types:

- **Draft demand letter** (15 examples) — generate structured demand letters from fact patterns
- **Identify claim** (10 examples) — determine the strongest legal claim from a scenario
- **Extract elements** (10 examples) — pull key elements (parties, damages, deadlines, remedies)
- **Evaluate letter** (7 examples) — assess whether a demand letter is complete and effective
- **Recommend remedy** (8 examples) — suggest appropriate legal remedies

## Adaptation Methods

Two approaches were used and compared:

1. **QLoRA Fine-Tuning** — Parameter-efficient fine-tuning using 4-bit quantization and LoRA adapters on an open-source LLM, trained on the instruction dataset.
2. **GEPA Prompt Optimization** — Evolutionary prompt optimization to improve domain-specific system prompts without modifying model weights.

## Evaluation

The `eval_4_configs.ipynb` notebook compares four configurations across the 10 evaluation queries:

1. Baseline (no adaptation)
2. GEPA-optimized prompts only
3. QLoRA fine-tuned model only
4. GEPA + QLoRA combined

Metrics: accuracy, domain relevance, hallucination rate, response clarity.
