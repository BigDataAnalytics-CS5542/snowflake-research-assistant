# Lab 8: Fine-Tuning and Domain Adaptation for GenAI Systems

## Course: CS 5542

## Deadline

- **Friday, March 13, 2026**
- Late submissions accepted until **Monday, March 15 at 12:00 PM (noon)** without penalty.

---

## Objective

Improve an existing course project by applying domain adaptation techniques. Instead of relying only on prompting or retrieval, teams will adapt a language model using:

- Instruction tuning
- Parameter-efficient fine-tuning (LoRA / QLoRA)
- Prompt adaptation

The adapted model must be integrated into the existing RAG / Streamlit / FastAPI pipeline, and teams must evaluate whether domain adaptation improves system performance.

---

## System Architecture

### Before (Baseline)

```
User Query → Prompt / RAG Retrieval → Foundation Model → Response
```

### After (Domain Adapted)

```
User Query → RAG Retrieval → Domain Adapted Model → Improved Response
```

The goal is to improve **domain reasoning**, not just document retrieval.

---

## Step-by-Step Lab Tasks

### Step 1 – Define Your Domain Task

Identify a specific domain reasoning task within the project. Describe:

- The domain task
- Expected model output
- Why domain adaptation may improve the system

| Project Type | Domain Task |
|---|---|
| Financial analysis | Analyze earnings reports |
| Drug safety | Detect adverse drug signals |
| Weather intelligence | Interpret hazard forecasts |
| Campus assistant | Answer university policy questions |
| Healthcare assistant | Explain clinical guidelines |

#### Domain Task Definition

This project focuses on the **legal demand** domain. The goal of the system is to assist with drafting, analyzing, and evaluating legal demand letters based on user-provided legal scenarios or existing draft letters.

The system uses a retrieval-augmented generation (RAG) pipeline to retrieve relevant statutes, legal templates, and case summaries. These sources provide contextual information that helps the model generate more accurate and domain-specific responses.

**Expected Outputs**

The system is designed to produce responses that include:

- properly structured demand letters
- identification of potential legal claims
- extraction of key elements such as parties, damages, deadlines, and remedies
- evaluation of whether a demand letter satisfies common legal requirements
- suggested remedies based on the identified claim

**Why Domain Adaptation Is Needed**

General-purpose language models often produce generic legal language and may fail to identify the correct legal elements required in a demand letter. Domain adaptation allows the model to better recognize legal claim patterns, understand the structure of demand letters, and produce clearer and more actionable legal responses.

By adapting the model to the legal demand domain, the system is expected to generate more precise legal reasoning, better structured demand letters, and improved identification of relevant remedies.

### Step 2 – Build an Instruction Dataset

Create a small instruction dataset (**20–50 examples**) in JSON or CSV format.

**Instruction format:**

```json
{
  "instruction": "Analyze the safety risk of this drug.",
  "input": "FDA adverse event report summary.",
  "output": "Risk explanation and potential concerns."
}
```

**Possible sources:** project dataset, research papers, domain documents, manually created examples, AI-generated examples.

### Step 3 – Apply Domain Adaptation

Choose one of the following:

**Option A – Parameter-Efficient Fine-Tuning (Preferred)**

- Tools: HuggingFace Transformers, PEFT (LoRA / QLoRA), Google Colab
- Suggested models: Mistral, Llama, Phi, or other open-source LLMs
- Workflow: Load base model → Load instruction dataset → Apply LoRA fine-tuning → Train → Save adapted model

**Option B – Instruction Prompt Adaptation**

- For teams with limited computational resources
- Approaches: structured system prompts, chain-of-thought prompting, prompt templates
- Must demonstrate clear improvement in responses

### Step 4 – Integrate into Project Pipeline

Update the project pipeline:

```
Streamlit UI → FastAPI backend → RAG retrieval → Domain-adapted model → Response
```

### Step 5 – Evaluate System Performance

Compare **baseline system vs. adapted system** using at least **10 evaluation queries**.

| Metric | Description |
|---|---|
| Accuracy | Correctness of responses |
| Domain relevance | Quality of reasoning |
| Hallucination rate | Incorrect information |
| Response clarity | Explanation quality |

### Step 6 – Update the Demo

Update the Streamlit interface to show:

- Baseline response
- Adapted response
- Improvement in reasoning

---

## Submission Requirements

### Group Submission (One per Team)

1. **Group Report (PDF, 1–2 pages)** including:
   - Project title and team members
   - Domain task definition
   - Instruction dataset description
   - Adaptation method used
   - System integration description
   - Evaluation results
   - Impact on project performance

2. **Contribution Table** (must total 100%)

   | Student Name | Contribution | Percentage |
   |---|---|---|
   | Student A | Instruction dataset creation, evaluation | 35% |
   | Student B | Fine-tuning implementation | 35% |
   | Student C | Streamlit integration and testing | 30% |

3. **GitHub Repository** containing:
   - Instruction dataset
   - Adaptation / fine-tuning scripts
   - Updated application code
   - Streamlit interface and FastAPI integration

### Individual Submission (Each Student)

Each student must submit a short report including:

- Description of their contributions
- Percentage contribution to the project
- GitHub commits or links demonstrating their work
- AI tools used and how they assisted development

---

## Evaluation Criteria

| Category | Points |
|---|---|
| Instruction dataset quality | 25 |
| Model adaptation implementation | 30 |
| Integration with project pipeline | 20 |
| Evaluation and analysis | 15 |
| Code quality and documentation | 10 |
| **Total** | **100** |

---

## Expected Outcome

The project should evolve from a **RAG-based chatbot** into a **domain-specialized AI assistant**, strengthening the final project and hackathon submission.

---

## AI Tools Policy

Students may use AI-assisted development tools (Antigravity, Claude, Cursor AI, other LLM-based assistants) but must clearly document their workflow, contributions, and use of AI tools in their reports.
