# Legal Demand Instruction Dataset Notes

## Domain
This project focuses on the **legal demand** domain. The system is designed to assist with drafting, analyzing, and evaluating demand letters based on legal fact patterns or draft letters.

## Purpose
The instruction dataset is intended to support domain adaptation for a legal-demand assistant. The goal is to improve performance beyond a generic baseline model by teaching the system how to:
- draft structured demand letters
- identify likely legal claims
- extract key demand letter elements
- evaluate whether a demand letter is complete and effective
- recommend appropriate remedies

## Dataset Format
Each example uses the following structure:

```json
{
  "id": "ld_001",
  "task_type": "draft_demand_letter",
  "instruction": "Draft a legal demand letter based on the scenario.",
  "input": "Fact pattern here...",
  "output": "Expected response here..."
}
```

## Final Dataset Summary
- Total examples: 50
- draft_demand_letter: 15
- identify_claim: 10
- extract_elements: 10
- evaluate_letter: 7
- recommend_remedy: 8