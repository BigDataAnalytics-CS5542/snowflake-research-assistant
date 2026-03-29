# Evaluation Queries for Legal Demand Domain

These queries will be used to compare:
1. Baseline
2. GEPA-optimized prompts
3. QLoRA fine-tuned model
4. GEPA + QLoRA combined

## Evaluation Query Set

### Q1 — Demand Letter Drafting
Draft a demand letter for a tenant whose landlord withheld a $2,500 security deposit without providing an itemized statement of damages.

### Q2 — Demand Letter Drafting
Draft a demand letter for a freelancer who completed branding work for a client, delivered the files, and never received the agreed $3,200 payment.

### Q3 — Claim Identification
Identify the strongest legal claim where a contractor accepted an $8,000 payment, performed minimal work, and abandoned the job.

### Q4 — Claim Identification
Identify the likely legal claim where a seller knowingly lied about a car having no accident history, and the buyer later discovered major prior damage.

### Q5 — Element Extraction
Extract the claimant, recipient, damages, deadline, and requested remedy from a demand letter involving water damage caused by a neighboring unit.

### Q6 — Element Extraction
Extract the key legal elements from a demand letter requesting reimbursement for unpaid wages and late compensation.

### Q7 — Letter Evaluation
Evaluate whether a demand letter is complete when it states only: "You owe me money. Please fix this immediately."

### Q8 — Letter Evaluation
Evaluate whether a demand letter is effective when it includes the dispute facts, damages, requested payment, and a 14-day response deadline.

### Q9 — Remedy Recommendation
Suggest appropriate remedies when a contractor took a deposit, abandoned a home repair project, and the homeowner had to hire another contractor for additional cost.

### Q10 — Remedy Recommendation
Suggest remedies for a consumer who purchased a defective appliance, repeatedly requested repair or refund, and received no response from the seller.

## Suggested Evaluation Criteria
- Accuracy
- Domain relevance
- Hallucination rate
- Response clarity
- Structure and professionalism