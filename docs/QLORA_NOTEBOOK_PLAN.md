# QLoRA Notebook Design Plan

Plan for the Colab notebook `training/qlora_finetune.ipynb` that fine-tunes a model on research paper tasks using QLoRA.

---

## Runtime

- Google Colab Pro with A100 GPU
- Expected training time: ~3 minutes for 50 examples

---

## Notebook Structure

### Cell 1: Install Dependencies

```
!pip install transformers>=4.46.0 peft>=0.13.0 bitsandbytes>=0.44.0 trl>=0.12.0 datasets accelerate flash-attn scikit-learn
```

### Cell 2: Imports and Configuration

All imports in one cell. Key hyperparameters defined as constants:

- `MODEL_ID = "Qwen/Qwen3.5-9B"`
- `OUTPUT_DIR = "./qlora-research-adapter"`
- LoRA: rank=16, alpha=32, dropout=0.1
- Target modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- Training: 3 epochs, lr=2e-4, cosine schedule, batch=2, grad_accum=4, max_seq_len=1024
- System prompt tailored to research paper analysis (summarize, compare methods, extract results, identify limitations, suggest related work)

### Cell 3: Upload and Load Instruction Dataset

- Upload `instruction_dataset.json` from local files or mount Google Drive
- Load the JSON file (30-50 examples across 5 task types)
- Format each example into ChatML messages: system prompt + user instruction/input + assistant output
- Print dataset stats (total examples, count per task type)

### Cell 4: Train/Val Split

- Stratified 90/10 split by `task_type` (e.g., 45 train / 5 val for 50 examples)
- Use `sklearn.model_selection.train_test_split` with `stratify=task_types`
- Drop `task_type` column after splitting (not needed for training)
- Print split sizes

### Cell 5: Load Model and Tokenizer (4-bit)

- Configure `BitsAndBytesConfig`: 4-bit NF4, double quantization, bfloat16 compute dtype
- Load tokenizer from `MODEL_ID`, set padding_side="right", pad_token=eos_token
- Load model with quantization config, flash_attention_2, device_map="auto"
- Disable KV cache (`model.config.use_cache = False`)
- Print model memory footprint

### Cell 6: Configure LoRA and Training

- Define `LoraConfig` with the hyperparameters from Cell 2
- Define `SFTConfig`: output_dir, epochs, batch sizes, gradient accumulation, learning rate, cosine scheduler, bf16, gradient checkpointing, eval/save per epoch, load_best_model_at_end
- Print trainable parameter count vs total parameters

### Cell 7: Train

- Initialize `SFTTrainer` with model, training config, train/val datasets, LoRA config, tokenizer
- Call `trainer.train()`
- Print training results: total steps, final loss, metrics per epoch
- Save adapter weights and tokenizer to `OUTPUT_DIR`

### Cell 8: Inference Test

- Reload the base model in 4-bit
- Load the saved adapter with `PeftModel.from_pretrained`
- Set model to eval mode
- Run 3 test prompts (one each for summarize_paper, compare_methods, extract_results) using chunks from our arXiv corpus as input context
- Apply chat template, generate with temperature=0.7, top_p=0.9, max_new_tokens=512
- Print each response

### Cell 9: Run Evaluation Queries

This is the cell that produces the precomputed responses for the backend.

- Define 10 evaluation queries (2 per task type), each with RAG context chunks pulled from our Snowflake corpus
- Run each query through the fine-tuned model
- Collect responses into a results dictionary structured as:
  ```json
  {
    "metadata": { "model": "...", "timestamp": "...", "num_queries": 10 },
    "detailed_results": {
      "qlora": [
        { "query_id": "Q1", "task_type": "summarize_paper", "query": "...", "response": "...", "score": null }
      ]
    }
  }
  ```
- Save to `eval_results.json`

### Cell 10: Download Artifacts

- Zip and download the adapter weights directory (`qlora-research-adapter/`)
- Download `eval_results.json`
- These two artifacts are what get committed to the main project repo:
  - Adapter weights go in `training/qlora-research-adapter/` (or hosted externally if too large)
  - Eval results go in `evaluation/qlora_eval_results.json` for the backend to serve

---

## Instruction Dataset Format

The notebook expects `instruction_dataset.json` with this structure:

```json
[
  {
    "task_type": "summarize_paper",
    "instruction": "Summarize the key contributions and findings of this research paper excerpt.",
    "input": "<chunk text from our arXiv corpus>",
    "output": "<gold-standard summary>"
  },
  {
    "task_type": "compare_methods",
    "instruction": "Compare the methodologies described in these research excerpts.",
    "input": "<two chunk texts>",
    "output": "<gold-standard comparison>"
  }
]
```

### Task Types

| Task Type | Count | Description |
|-----------|-------|-------------|
| `summarize_paper` | 6-10 | Summarize a paper's key contributions from a chunk |
| `compare_methods` | 6-10 | Compare approaches across two excerpts |
| `extract_results` | 6-10 | Pull out quantitative results and findings |
| `identify_limitations` | 6-10 | Surface weaknesses and gaps in the research |
| `suggest_related_work` | 6-10 | Recommend related directions based on an excerpt |

---

## Outputs

The notebook produces two artifacts that the main project needs:

1. **`qlora-research-adapter/`** — LoRA adapter weights (~116 MB based on Lab 8). Contains `adapter_config.json`, `adapter_model.safetensors`, tokenizer files.

2. **`qlora_eval_results.json`** — Precomputed responses for 10 evaluation queries. This is what the FastAPI backend loads and serves when users select QLoRA mode. No live model inference needed at serving time.

---

## Differences from Lab 8 Notebook

| Aspect | Lab 8 | This Notebook |
|--------|-------|---------------|
| Domain | Legal demand letters | Research paper analysis |
| System prompt | Legal demand assistant | Research paper assistant |
| Task types | draft_demand_letter, identify_claim, extract_elements, evaluate_letter, recommend_remedy | summarize_paper, compare_methods, extract_results, identify_limitations, suggest_related_work |
| Dataset source | Hand-written legal scenarios | Chunks from our arXiv corpus in Snowflake + Gemini-generated gold outputs |
| Eval context | Standalone queries | Queries with RAG-retrieved chunks (to match how the main project works) |
| Model & hyperparameters | Same | Same |
| Quantization config | Same | Same |
| LoRA config | Same | Same |
