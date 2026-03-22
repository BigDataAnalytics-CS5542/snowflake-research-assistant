# Instruction Dataset Generation Plan

Plan for building the instruction dataset (`data/instruction_dataset.json`) that the QLoRA notebook consumes for fine-tuning.

---

## Goal

Produce 30-50 instruction/input/output examples across 5 research paper task types, sourced from our existing arXiv corpus in Snowflake.

---

## Approach

1. Pull diverse chunks from Snowflake as raw material
2. Use Gemini (our existing LLM) to generate gold-standard outputs for each task type
3. Manually review and correct the generated outputs
4. Save as `data/instruction_dataset.json`

This can be done as a Jupyter notebook (`training/generate_dataset.ipynb`) run locally or on Colab.

---

## Notebook Structure

### Cell 1: Imports and Configuration

- Snowflake connector (reuse `scripts/sf_connect.py`)
- Google Gemini client (same setup as `backend/app.py`)
- JSON, random, os
- Constants: number of examples per task type, Gemini model ID

### Cell 2: Connect to Snowflake and Pull Chunks

Query a diverse sample of chunks from the corpus:

```sql
SELECT c.CHUNK_ID, c.CHUNK_TEXT, c.SECTION, p.PAPER_ID, p.TITLE, p.ABSTRACT
FROM RAW.CHUNKS c
JOIN RAW.PAPERS p ON c.PAPER_ID = p.PAPER_ID
ORDER BY RANDOM()
LIMIT 200;
```

Pull more than we need (200) so we can pick the best candidates. Filter out chunks that are too short, mostly references, or mostly equations — these make poor training examples.

### Cell 3: Define Task Templates

Each task type gets an instruction template and a Gemini prompt that tells Gemini how to produce the gold-standard output.

```python
TASKS = {
    "summarize_paper": {
        "instruction": "Summarize the key contributions and findings of this research paper excerpt.",
        "gemini_prompt": "Read the following research paper excerpt and write a concise 3-5 sentence summary of its key contributions and findings. Be specific about methods and results mentioned.",
        "chunks_needed": 1,  # single chunk per example
    },
    "compare_methods": {
        "instruction": "Compare the methodologies described in these two research excerpts.",
        "gemini_prompt": "Read the following two research paper excerpts and write a comparison of their methodologies. Identify similarities, differences, and relative strengths.",
        "chunks_needed": 2,  # pair of chunks per example
    },
    "extract_results": {
        "instruction": "Extract the key experimental results and findings from this research excerpt.",
        "gemini_prompt": "Read the following research paper excerpt and extract all quantitative results, metrics, baselines, and key findings. Present them in a structured format.",
        "chunks_needed": 1,
    },
    "identify_limitations": {
        "instruction": "Identify the limitations and potential weaknesses in this research.",
        "gemini_prompt": "Read the following research paper excerpt and identify any limitations, weaknesses, assumptions, or gaps. Include both limitations the authors acknowledge and any you can infer.",
        "chunks_needed": 1,
    },
    "suggest_related_work": {
        "instruction": "Based on this research excerpt, suggest related research directions and adjacent fields worth exploring.",
        "gemini_prompt": "Read the following research paper excerpt and suggest 3-5 related research directions, adjacent fields, or follow-up studies that would build on this work. Be specific.",
        "chunks_needed": 1,
    },
}
```

### Cell 4: Select Candidate Chunks per Task Type

Not all chunks work well for all tasks:

- **summarize_paper**: Pick chunks from abstract or introduction sections that describe the paper's purpose and approach
- **compare_methods**: Pick pairs of chunks from different papers that discuss similar topics (use embedding similarity to find pairs from different papers)
- **extract_results**: Pick chunks from results/experiments/evaluation sections that contain numbers and metrics
- **identify_limitations**: Pick chunks from discussion/conclusion sections, or methodology sections with stated assumptions
- **suggest_related_work**: Pick chunks from introduction or related work sections that establish the research context

Select 8-12 candidate chunks per task type (more than the 6-10 we need, so we can drop weak examples after review).

### Cell 5: Generate Gold-Standard Outputs with Gemini

For each selected chunk + task type combination:

1. Build a prompt combining the task's `gemini_prompt` with the chunk text
2. Call Gemini to generate the output
3. Store the result

```python
for task_type, config in TASKS.items():
    for chunk_group in selected_chunks[task_type]:
        if config["chunks_needed"] == 1:
            input_text = chunk_group["chunk_text"]
        else:
            input_text = f"Excerpt 1:\n{chunk_group[0]['chunk_text']}\n\nExcerpt 2:\n{chunk_group[1]['chunk_text']}"

        gemini_prompt = f"{config['gemini_prompt']}\n\n{input_text}"
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=gemini_prompt,
        )

        dataset.append({
            "task_type": task_type,
            "instruction": config["instruction"],
            "input": input_text,
            "output": response.text,
        })
```

### Cell 6: Review and Print Examples

Display all generated examples for manual review:

- Print each example with task type, instruction, input preview (first 200 chars), and full output
- Flag any outputs that look generic, hallucinated, or low quality
- Print distribution summary (count per task type)

### Cell 7: Manual Corrections

A cell with a list of indices to drop or replace:

```python
# Drop weak examples
drop_indices = [3, 17, 28]  # fill in after review
dataset = [ex for i, ex in enumerate(dataset) if i not in drop_indices]

# Manual corrections (fill in after review)
# dataset[5]["output"] = "corrected output..."
```

### Cell 8: Save Dataset

```python
with open("instruction_dataset.json", "w") as f:
    json.dump(dataset, f, indent=2)

print(f"Saved {len(dataset)} examples")
for task_type in TASKS:
    count = sum(1 for ex in dataset if ex["task_type"] == task_type)
    print(f"  {task_type}: {count}")
```

Download the file for placement in `data/instruction_dataset.json` in the main project.

---

## Output Format

```json
[
  {
    "task_type": "summarize_paper",
    "instruction": "Summarize the key contributions and findings of this research paper excerpt.",
    "input": "We propose a novel attention mechanism that reduces the quadratic complexity of standard transformers to linear...",
    "output": "This paper introduces a linear-complexity attention mechanism that..."
  }
]
```

---

## Chunk Selection Criteria

Good chunks for training should be:

- **Substantive**: 100-200 words of actual content (not references, acknowledgments, or boilerplate)
- **Self-contained**: Makes sense without needing the rest of the paper
- **Diverse**: From different papers and different topics within the corpus
- **Section-appropriate**: Matched to the task type (results sections for extract_results, etc.)

Bad chunks to filter out:

- Mostly equations or mathematical notation
- Reference lists or bibliographies
- Very short stubs or section headers
- Acknowledgment or funding sections

---

## Quality Checklist

Before the dataset is used for training:

- [ ] At least 30 examples total, no more than 50
- [ ] 6-10 examples per task type (balanced distribution)
- [ ] All Gemini-generated outputs reviewed manually
- [ ] Outputs are grounded in the input text (no hallucinated claims)
- [ ] Outputs are the right length and format for each task type
- [ ] No duplicate chunks used across examples
- [ ] Input chunks come from a diverse set of papers (not all from the same 5 papers)
