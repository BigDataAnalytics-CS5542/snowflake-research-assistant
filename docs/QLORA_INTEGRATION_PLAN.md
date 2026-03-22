# Applying QLoRA Fine-Tuning to the Research Assistant

This document outlines how to integrate QLoRA (Quantized Low-Rank Adaptation) fine-tuning into the Snowflake Research Assistant project, adapting the approach proven in Lab 8 (legal demand letters) to our research paper domain.

---

## Background

In Lab 8, we built a standalone QLoRA fine-tuning pipeline for legal demand letters using Qwen3.5-9B. That pipeline achieved 95% accuracy across 5 task types. However, it was never integrated into the main research assistant project. This document covers what needs to change to bring QLoRA into our existing Snowflake + RAG + Knowledge Graph architecture.

---

## 1. Define Research Paper Task Types

Lab 8 used 5 legal task types. We need equivalent task types for the research paper domain:

| Task Type | Description | Example Prompt |
|-----------|-------------|----------------|
| `summarize_paper` | Produce a concise summary of a paper's contributions | "Summarize the key contributions of this paper on transformer architectures." |
| `compare_methods` | Compare methodologies across papers | "Compare the training approaches described in these two excerpts." |
| `extract_results` | Pull out quantitative results and findings | "Extract the main experimental results from this section." |
| `identify_limitations` | Surface weaknesses and gaps in the research | "What limitations does the author acknowledge in this work?" |
| `suggest_related_work` | Recommend related papers or research directions | "Based on this abstract, what related research areas should be explored?" |

These tasks map well to what a research assistant should do and give us structured outputs we can evaluate.

---

## 2. Build the Instruction Dataset

**Target:** 30-50 instruction examples in JSON format, sourced from our existing arXiv corpus in Snowflake.

### Dataset Format

Each example follows the same structure used in Lab 8:

```json
{
  "task_type": "summarize_paper",
  "instruction": "Summarize the key contributions and findings of this research paper excerpt.",
  "input": "<chunk text from Snowflake RAW.CHUNKS>",
  "output": "<gold-standard summary>"
}
```

### How to Generate Examples

1. **Pull representative chunks** from Snowflake across different paper topics:
   ```sql
   SELECT c.CHUNK_TEXT, p.TITLE, p.ABSTRACT, c.SECTION
   FROM RAW.CHUNKS c
   JOIN RAW.PAPERS p ON c.PAPER_ID = p.PAPER_ID
   ORDER BY RANDOM()
   LIMIT 100;
   ```

2. **Use Gemini (our existing LLM) to generate gold-standard outputs** for each task type, then manually review and correct them. This is the same approach documented in our fine-tuning guide — use a stronger model to create training data.

3. **Aim for balanced distribution**: ~6-10 examples per task type.

4. **Save as** `data/instruction_dataset.json` in the project root.

---

## 3. QLoRA Training Script

Port `Lab_8/training/qlora_finetune.py` into the project with these modifications:

### File Location
```
snowflake-research-assistant/
└── training/
    ├── qlora_finetune.py          # Adapted training script
    ├── qlora_finetune.ipynb        # Colab notebook version
    └── README.md                   # Training instructions
```

### Key Changes from Lab 8

| Parameter | Lab 8 (Legal) | Research Assistant |
|-----------|---------------|-------------------|
| `MODEL_ID` | `Qwen/Qwen3.5-9B` | `Qwen/Qwen3.5-9B` (keep same) |
| `OUTPUT_DIR` | `./qlora-legal-demand-adapter` | `./qlora-research-adapter` |
| `DATA_PATH` | `../data/instruction_dataset.json` | `../data/instruction_dataset.json` |
| `SYSTEM_PROMPT` | Legal demand assistant | Research paper assistant (see below) |
| `NUM_EPOCHS` | 3 | 3 (keep same) |
| `LORA_R` | 16 | 16 (keep same) |
| `MAX_SEQ_LENGTH` | 1024 | 1024 (may increase to 2048 if paper chunks are long) |

### Updated System Prompt

```python
SYSTEM_PROMPT = (
    "You are a research paper assistant specialized in analyzing scientific literature. "
    "You help summarize papers, compare methodologies, extract experimental results, "
    "identify limitations, and suggest related research directions. "
    "Always ground your responses in the provided text and be precise about claims."
)
```

### QLoRA Configuration (Unchanged)

The quantization and LoRA settings from Lab 8 are model-dependent, not domain-dependent. Keep them as-is:

- **Quantization:** 4-bit NF4 with double quantization (~7.5 GB VRAM)
- **LoRA:** rank=16, alpha=32, dropout=0.1
- **Targets:** q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- **Training:** lr=2e-4, cosine schedule, batch=2, grad_accum=4, bf16

### Training Environment

Same as Lab 8 — Google Colab Pro with A100 GPU. Expected training time: ~3 minutes for 50 examples.

Required packages:
```
transformers>=4.46.0
peft>=0.13.0
bitsandbytes>=0.44.0
trl>=0.12.0
datasets
accelerate
flash-attn
```

---

## 4. Backend Integration

The main integration point is `backend/app.py`. Currently, all queries go through the Gemini agentic loop. We need to add a model selection mechanism.

### 4a. Add a `mode` Parameter to the Query Endpoint

Update `QueryRequest` in `backend/app.py`:

```python
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    passcode: str = ""
    mode: str = "agentic"  # "agentic" (default) | "qlora" | "comparison"
```

### 4b. Add QLoRA Inference Module

Create `backend/qlora_inference.py`:

```python
"""
QLoRA inference for the research assistant.
Loads the fine-tuned adapter and generates responses.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

MODEL_ID = "Qwen/Qwen3.5-9B"
ADAPTER_PATH = "./qlora-research-adapter"

SYSTEM_PROMPT = (
    "You are a research paper assistant specialized in analyzing scientific literature. "
    "You help summarize papers, compare methodologies, extract experimental results, "
    "identify limitations, and suggest related research directions. "
    "Always ground your responses in the provided text and be precise about claims."
)

_model = None
_tokenizer = None

def load_qlora_model():
    """Load base model + QLoRA adapter. Cached after first call."""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    _tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    _model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    _model.eval()
    return _model, _tokenizer


def generate_qlora_response(question: str, context_chunks: list[str]) -> str:
    """
    Generate a response using the QLoRA fine-tuned model.

    Args:
        question: The user's question
        context_chunks: Retrieved text chunks from Snowflake (RAG context)

    Returns:
        The model's generated response
    """
    model, tokenizer = load_qlora_model()

    # Build the prompt with RAG context
    context_block = "\n\n".join(
        f"[{i+1}] {chunk}" for i, chunk in enumerate(context_chunks)
    )
    user_content = (
        f"Using the following research paper excerpts as context:\n\n"
        f"{context_block}\n\n"
        f"Question: {question}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
        )

    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    return response.strip()
```

### 4c. Route Queries by Mode

In `backend/app.py`, update `_query_logic` to branch on `req.mode`:

```python
def _query_logic(req: QueryRequest):
    start = time.time()
    conn = get_active_conn(passcode=req.passcode.strip())

    if req.mode == "qlora":
        # Step 1: Retrieve chunks via vector search (same RAG retrieval)
        chunks = get_top_chunks(conn=conn, query_text=req.question, top_k=req.top_k)
        context_texts = [chunk[5] for chunk in chunks]
        citations = [...]  # build citation list same as current code

        # Step 2: Generate with QLoRA model instead of Gemini
        from backend.qlora_inference import generate_qlora_response
        answer = generate_qlora_response(req.question, context_texts)

        return {
            'answer': answer,
            'citations': citations,
            'confidence': chunks[0][0] if chunks else 0.0,
            'retrieval_mode': 'qlora',
            'latency_ms': int((time.time() - start) * 1000)
        }

    elif req.mode == "comparison":
        # Run both and return side-by-side (for evaluation/demo)
        ...

    else:
        # Default: existing Gemini agentic loop (unchanged)
        ...
```

### 4d. Important Consideration: GPU Requirements

The current backend runs on CPU (Gemini is called via API). Adding QLoRA inference requires a GPU on the serving machine. Options:

1. **Colab-hosted inference** — Run the QLoRA model in Colab and expose via ngrok or a simple Flask endpoint. The FastAPI backend calls this external endpoint instead of loading the model locally.
2. **Precomputed responses** — For demo/evaluation purposes, run inference in Colab on the evaluation queries and store results. The backend serves precomputed responses when `mode=qlora`. This is what Lab 8 did.
3. **Local GPU** — If a team member has a GPU with 8+ GB VRAM, run the model locally alongside FastAPI.

**Recommendation:** Use option 2 (precomputed) for the demo and evaluation, with option 1 as a stretch goal. This avoids GPU dependency in the main pipeline while still showing the comparison.

---

## 5. Frontend Integration

Update `frontend/app.py` to add a model selector in the sidebar:

```python
with st.sidebar:
    st.header("Settings")
    # ... existing MFA code ...

    st.markdown("---")
    st.header("Model Configuration")
    mode = st.radio(
        "Response Mode",
        options=["agentic", "qlora", "comparison"],
        format_func=lambda x: {
            "agentic": "Gemini Agentic RAG (Default)",
            "qlora": "QLoRA Fine-Tuned",
            "comparison": "Side-by-Side Comparison",
        }[x],
        index=0,
    )
```

Then pass `mode` in the query payload:

```python
payload = {
    "question": prompt,
    "top_k": 5,
    "passcode": passcode,
    "mode": mode,
}
```

For comparison mode, display results side-by-side using `st.columns(2)`.

---

## 6. Evaluation Plan

Following Lab 8's approach, evaluate with at least 10 queries across our 5 task types (2 per type).

### Evaluation Queries (Examples)

1. **summarize_paper**: "Summarize the main contributions of this paper on attention mechanisms."
2. **summarize_paper**: "What are the key findings presented in this study on neural architecture search?"
3. **compare_methods**: "Compare the training strategies described in these two paper excerpts."
4. **compare_methods**: "How do the optimization approaches in these passages differ?"
5. **extract_results**: "What quantitative results are reported in this experimental section?"
6. **extract_results**: "Extract the accuracy numbers and baselines mentioned here."
7. **identify_limitations**: "What limitations does the author discuss?"
8. **identify_limitations**: "What potential weaknesses can you identify in this methodology?"
9. **suggest_related_work**: "What related research directions does this work point to?"
10. **suggest_related_work**: "Based on this abstract, what adjacent fields might benefit from this approach?"

### Metrics

Score each response on:
- **Accuracy** (0-100%): Is the information correct?
- **Completeness** (0-100%): Does it cover all key points?
- **Grounding** (0-100%): Is it grounded in the provided context?

Compare across configurations:
1. Baseline (Gemini agentic RAG — current system)
2. QLoRA fine-tuned + RAG retrieval

---

## 7. Implementation Checklist

- [ ] Create `data/instruction_dataset.json` with 30-50 research paper examples
- [ ] Create `training/` directory with adapted QLoRA script
- [ ] Train adapter on Colab (save to `qlora-research-adapter/`)
- [ ] Create `backend/qlora_inference.py`
- [ ] Add `mode` parameter to `QueryRequest` in `backend/app.py`
- [ ] Add mode routing logic in `_query_logic`
- [ ] Add model selector to `frontend/app.py` sidebar
- [ ] Run evaluation queries across both modes
- [ ] Document results in `evaluation/results.md`
- [ ] Update `README.md` with fine-tuning section
- [ ] Update `requirements.txt` with training dependencies

---

## 8. New Dependencies

Add to `requirements.txt` (needed only for training and local inference):

```
# QLoRA Fine-Tuning (install on training machine / Colab)
peft>=0.13.0
bitsandbytes>=0.44.0
trl>=0.12.0
accelerate
```

Note: `transformers` and `datasets` are likely already in requirements. `flash-attn` is Colab-only and should not be in the main requirements file.

---

## Summary

The core insight is that QLoRA is domain-agnostic — the training pipeline from Lab 8 transfers directly. What changes is:
1. The **instruction dataset** (research papers instead of legal demands)
2. The **system prompt** (research assistant instead of legal assistant)
3. The **integration points** (mode toggle in the existing FastAPI/Streamlit pipeline)

Everything else — model choice, quantization config, LoRA hyperparameters, training loop — stays the same.
