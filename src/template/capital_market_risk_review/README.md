# Capital Market Risk Review — Template

## What this template does

End-to-end LangGraph pipeline that:
1. Ingests raw risk documents
2. Splits + embeds them into a vector store
3. Retrieves top-k most relevant chunks
4. Runs LLM analysis to produce a draft summary + structured JSON findings
5. Pauses for Human-in-the-Loop (HITL) review
6. Resumes with human decision: approve / edit / reject
7. Produces a final approved summary

---

## File structure

```
src/template/capital_market_risk_review/
├── __init__.py     ← package marker
├── models.py       ← domain schemas (RiskFinding, ReviewState)
├── ingest.py       ← document loading and chunking
├── analyze.py      ← LLM risk analysis and findings extraction
├── review.py       ← HITL pause, routing, finalization
├── graph.py        ← LangGraph pipeline assembly
├── main.py         ← entry point / demo runner
└── README.md       ← this file
```

---

## Run locally

```powershell
# Set your API key
$env:OPENAI_API_KEY="your_key_here"

# Run the pipeline
python -m src.template.capital_market_risk_review.main
```

---

## Graph flow

```
START
  └── ingest          split documents into overlapping chunks
       └── retrieve   embed + similarity search top-k chunks
            └── analyze    LLM draft summary + JSON findings
                 └── human_review   HITL interrupt (pause here)
                      └── finalize  apply approve/edit/reject
                           └── END
```

---

## Extension points summary

| File | What to extend |
|---|---|
| `models.py` | Add risk categories, severity scores, regulatory fields |
| `ingest.py` | Swap InMemoryVectorStore → pgvector/Chroma, add PDF/Word loaders |
| `analyze.py` | Swap gpt-4o-mini → gpt-4o, add structured output, self-critique |
| `review.py` | Add multi-tier approval, Slack/email notifications, audit log |
| `graph.py` | Add parallel branches, critique node, report generation node |
| `main.py` | Add CLI args, batch mode, real document file loading |

---

## HITL flow in code

```python
# Step 1: Run until interrupt
paused_state = graph.invoke(initial_state, config=config)

# Step 2: Resume with human decision (same thread_id)
final_state = graph.invoke(
    {"human_decision": "approve"},
    config=config,
)
```

