# Capital Market Risk Review — Design Document Template

## 1. Document Control
- **Owner:** <team-or-person>
- **Reviewers:** <names>
- **Version:** 0.1.0
- **Last Updated:** 2026-06-05
- **Status:** Draft

---

## 2. Purpose and Scope
This document describes the design of the `capital_market_risk_review` LangGraph template and captures both:
1. **Current implementation** (what is already built)
2. **Extension design template** (what to fill in for production)

### In Scope
- Risk document ingestion and chunking
- Retrieval-augmented analysis
- Structured findings extraction
- Human-in-the-loop (HITL) approval

### Out of Scope (current template)
- Persistent vector database
- Enterprise authn/authz
- Full audit database integration
- Production monitoring/alerting

---

## 3. Current Implementation (As-Is)

### 3.1 Folder and Modules
- `models.py` — domain and state schema (`RiskFinding`, `ReviewState`)
- `ingest.py` — chunking + in-memory retrieval setup
- `analyze.py` — LLM-based summary and findings extraction
- `review.py` — HITL interrupt, route, and finalization
- `graph.py` — graph assembly and checkpointing
- `main.py` — runnable demo flow

### 3.2 State Contract (`ReviewState`)
Core state fields used now:
- `raw_docs`: list of source texts
- `query`: retrieval focus
- `chunks`: split documents
- `retrieved`: top-k retrieved chunks
- `draft_summary`: LLM draft
- `findings_json`: structured findings payload
- `human_decision`: `approve | edit | reject | None`
- `edited_summary`: optional edited text
- `final_summary`: output after approval flow

### 3.3 Runtime Graph Flow
`START -> ingest -> retrieve -> analyze -> human_review -> finalize -> END`

Behavior:
1. `ingest`: split docs into overlapping chunks
2. `retrieve`: embed + similarity search relevant chunks
3. `analyze`: generate draft summary and findings JSON text
4. `human_review`: pause execution via interrupt until decision is supplied
5. `finalize`: apply decision and produce `final_summary`

### 3.4 HITL Pause/Resume
The graph uses checkpointing and a stable `thread_id`.
- First invoke pauses at `human_review`
- Second invoke (same `thread_id`) resumes with input like:
  - `{ "human_decision": "approve" }`
  - `{ "human_decision": "edit", "edited_summary": "..." }`
  - `{ "human_decision": "reject" }`

---

## 4. Architecture Decisions (Current)
- **Graph engine:** LangGraph with typed state
- **LLM:** `ChatOpenAI` (`gpt-4o-mini` in template)
- **Embeddings:** `OpenAIEmbeddings`
- **Vector store:** in-memory (for demo simplicity)
- **Checkpointing:** `MemorySaver` (demo-level persistence)

Rationale: prioritize readability and fast local experimentation.

---

## 5. Known Gaps / Risks (Current)
1. In-memory vector store is not durable
2. Findings are JSON text, not strict schema-validated objects
3. No authentication for human approvals
4. No explicit audit trail storage (who approved, when)
5. No retry/backoff + rate-limit policy documented

---

## 6. Extension Template (To-Be)

### 6.1 Functional Requirements
- FR1: <fill>
- FR2: <fill>
- FR3: <fill>

### 6.2 Non-Functional Requirements
- Latency: <target>
- Throughput: <target>
- Availability: <target>
- Security/Compliance: <target>

### 6.3 Data & Storage Design
- Vector DB: <pgvector/chroma/azure ai search>
- Checkpoint store: <sqlite/postgres>
- Audit store: <postgres/cosmos/sql>
- Retention: <policy>

### 6.4 Security Design
- Secret management: <Key Vault / env strategy>
- Access control: <RBAC model>
- PII controls: <masking/redaction policy>

### 6.5 Human Review UX
- Review channel: <web/slack/email>
- Approval levels: <single/multi-tier>
- SLA and escalation: <rules>

### 6.6 Observability
- Tracing: <LangSmith>
- Metrics: <latency, token usage, failure rate>
- Alerting: <pager/email>

---

## 7. Suggested Production Roadmap
1. Replace in-memory retrieval with persistent vector DB
2. Add strict structured output validation (Pydantic)
3. Add durable checkpoint + audit logs
4. Add reviewer identity capture and RBAC
5. Add evaluation dataset + regression tests

---

## 8. Testing Strategy Template
- Unit: node-level logic (`ingest`, `review`, `route_after_review`)
- Integration: end-to-end flow with mocked LLM
- HITL: pause/resume correctness with same `thread_id`
- Failure tests: invalid JSON, missing decision, empty docs

---

## 9. Operations Runbook Template
- Deploy process: <steps>
- Rollback process: <steps>
- Incident response owner: <name>
- Common failure signatures: <list>

---

## 10. Decision Log
- [2026-06-05] Initial template and as-is design documented.

