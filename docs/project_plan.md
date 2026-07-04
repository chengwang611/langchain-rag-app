# Capital Market Risk Review — Production Project Plan

> Estimated timeline for a typical tier-1 bank IT team to take the current
> implementation to a full production-grade capital market risk review system.

---

## 1. The "Bank Multiplier" Effect

Bank IT moves **3-5x slower** than Big Tech or startups due to compliance, procurement, and legacy integration overhead.

| Factor | Big Tech / Startup | Bank | Multiplier |
|---|---|---|---|
| **Procurement** | Credit card, done | 6-week vendor security review + 4-week PO | 3x |
| **Compliance review** | None | Architecture review, security review, privacy review, model risk review | 4x |
| **Change management** | PR merged, deployed | CAB approval, change window (weekly/monthly), rollback plan | 3x |
| **Data access** | API key, done | 4-week data classification review, 2-week entitlement setup | 6x |
| **Legacy integration** | Modern API | Mainframe batch, MQ queues, file drops, screen scraping | 5x |
| **Testing** | CI/CD pipeline | Unit + integration + UAT + performance + security + regression + parallel run | 3x |

---

## 2. Phase-by-Phase Timeline

### Phase 1: Foundation (P0) — 4-6 months

| Feature | Pure Dev Time | Bank Total | Key Bottleneck |
|---|---|---|---|
| Immutable audit trail | 2 weeks | **6-8 weeks** | Database compliance review, data retention policy sign-off |
| Multi-jurisdiction regulatory rules | 3 weeks | **8-10 weeks** | Legal/compliance review of each jurisdiction's regulatory text |
| RBAC + Azure AD SSO | 3 weeks | **8-12 weeks** | Enterprise IAM team dependency, security review, entitlement process |
| **Phase 1 Total** | **8 weeks** | **4-6 months** | |

### Phase 2: Operational (P1) — 4-8 months

| Feature | Pure Dev Time | Bank Total | Key Bottleneck |
|---|---|---|---|
| Finding lifecycle management | 3 weeks | **6-8 weeks** | Workflow approval from risk operations team |
| SLA tracking + escalation | 2 weeks | **4-6 weeks** | SLA definition sign-off from business, legal review of escalation terms |
| Live market data feeds (Bloomberg) | 6 weeks | **12-16 weeks** | Bloomberg license procurement, market data entitlement, network connectivity |
| **Phase 2 Total** | **11 weeks** | **4-8 months** | |

### Phase 3: Completeness (P2) — 3-6 months

| Feature | Pure Dev Time | Bank Total | Key Bottleneck |
|---|---|---|---|
| Board report generation | 3 weeks | **6-8 weeks** | Report format approval from board reporting team |
| Stress testing scenarios | 6 weeks | **8-12 weeks** | Scenario definition sign-off from risk methodology team |
| Power BI dashboard | 4 weeks | **8-12 weeks** | Data source certification, dashboard design review |
| **Phase 3 Total** | **13 weeks** | **3-6 months** | |

### Phase 4: Advanced (P3) — 6-12 months

| Feature | Pure Dev Time | Bank Total | Key Bottleneck |
|---|---|---|---|
| Climate risk (NGFS scenarios) | 8 weeks | **12-16 weeks** | Regulatory methodology still evolving, model risk approval |
| CCAR / DFAST (US regulatory stress) | 12 weeks | **16-24 weeks** | Fed supervisory approval, parallel run with existing process |
| Multi-region disaster recovery | 6 weeks | **12-16 weeks** | Infrastructure procurement, DR test window scheduling |
| **Phase 4 Total** | **26 weeks** | **6-12 months** | |

---

## 3. Overall Timeline

```
Phase 1 (P0):  ████████████████████░░░░░░░░░░░░  4-6 months
Phase 2 (P1):  ░░░░░████████████████████░░░░░░  4-8 months  (starts month 4)
Phase 3 (P2):  ░░░░░░░░░░████████████████░░░░  3-6 months  (starts month 8)
Phase 4 (P3):  ░░░░░░░░░░░░░░░░██████████████  6-12 months (starts month 12)

Total: 18-32 months (1.5 - 2.5 years)
```

### By Team Size

| Scenario | Timeline | Team Size | Conditions |
|---|---|---|---|
| **Aggressive** | **12-18 months** | 6 people (3 senior, 2 mid, 1 junior) | Dedicated team, existing platform, minimal compliance friction |
| **Realistic** | **18-24 months** | 4-5 people (2 senior, 2 mid, 1 junior) | Shared team, standard bank processes |
| **Conservative** | **24-36 months** | 3-4 people (1 senior, 2 mid, 1 junior) | New platform, heavy compliance, many dependencies |

---

## 4. Accelerators vs Bottlenecks

### What Makes It Faster

| Accelerator | Time Saved | Why |
|---|---|---|
| **Existing Bloomberg license** | 2-3 months | Skip procurement hell |
| **Already on Azure** | 1-2 months | No cloud procurement, existing networking |
| **Existing PGVector / Postgres** | 1 month | No database procurement or DBA setup |
| **Existing Azure AD integration** | 1-2 months | IAM team already has SSO patterns |
| **Dedicated compliance liaison** | 2-3 months | Reviews queued faster, no waiting for quarterly cycles |
| **Agile procurement (enterprise agreement)** | 1-2 months | No per-vendor PO cycles |

### What Makes It Slower

| Bottleneck | Time Added | Why |
|---|---|---|
| **First-time Bloomberg integration** | 3-4 months | License, network, entitlement, testing |
| **No existing Azure footprint** | 3-6 months | Cloud strategy, landing zone, networking, security baseline |
| **Mainframe data dependency** | 3-6 months | Batch window scheduling, data extraction, reconciliation |
| **Model risk approval (SR 11-7)** | 3-6 months | Independent model validation, documentation, committee approval |
| **Regulator notification** | 2-4 months | Some jurisdictions require notification before changing risk systems |
| **Parallel run period** | 2-4 months | Old and new system must run in parallel before decommissioning |

---

## 5. Team Composition

### Recommended Team for 18-Month Delivery

| Role | Count | Responsibilities |
|---|---|---|
| **Senior Backend Engineer** (Python) | 2 | Core pipeline, API, agent logic, code review |
| **Data Engineer** (Spark, Databricks) | 1 | Embedding pipeline, data quality, performance tuning |
| **DevOps / Cloud Engineer** (Azure) | 1 | Infrastructure, CI/CD, monitoring, DR |
| **Risk Domain SME** | 1 | Regulatory rules, scenario definitions, acceptance testing |
| **QA / Test Engineer** | 1 | Test automation, parallel run validation, regression |

**Total: 6 people**

### Key Skills Required

- **Python** (LangGraph, LangChain, FastAPI, PySpark)
- **Azure** (ACA, ACR, PostgreSQL, Key Vault, Azure AD, Databricks)
- **Financial domain** (Basel III/IV, VaR, CVA, RWA, CCAR, DFAST)
- **Data engineering** (Spark, Delta Lake, vector databases, ETL pipelines)

---

## 6. Comparison: Solo Dev vs Bank Team

| Metric | You (solo dev) | Bank IT Team (4-6 people) |
|---|---|---|
| **Current project (what exists now)** | ~3 months | **6-9 months** (compliance + architecture review + procurement) |
| **Phase 1 (P0)** | 2-3 months | **4-6 months** |
| **Full production (all phases)** | 6-9 months | **18-24 months** |
| **Lines of code** | ~3,000 | Similar (but 50% is boilerplate, config, and compliance logging) |
| **Decision latency** | Minutes | Weeks (architecture review board meets bi-weekly) |
| **Deployment** | `git push` | CAB approval + change window + rollback plan |

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Bloomberg procurement delay | High | High | Start procurement in parallel with Phase 1 |
| Model risk approval rejection | Medium | High | Engage model risk team early, document methodology thoroughly |
| Legacy system data quality issues | High | Medium | Data validation layer, reconciliation reports |
| Regulatory requirement changes | Medium | Medium | Modular rule engine, parameter-driven thresholds |
| Key person dependency | Medium | High | Cross-training, documentation, pair programming |
| Cloud cost overrun | Medium | Medium | Cost budgeting, auto-scaling limits, reserved instances |

---

## 8. Key Milestones

| Milestone | Month | Deliverable |
|---|---|---|
| **Architecture review approved** | M1 | Design document signed off by architecture review board |
| **Security review passed** | M2 | Threat model, data classification, access control approved |
| **Phase 1 MVP** | M6 | Audit trail + multi-jurisdiction rules + RBAC deployed to production |
| **Bloomberg feed live** | M10 | Real-time market data flowing, VaR/CVA using live data |
| **Phase 2 complete** | M12 | Finding lifecycle + SLA tracking operational |
| **Parallel run begins** | M14 | Old and new system running in parallel |
| **Phase 3 complete** | M16 | Board reports + stress testing + dashboards |
| **Regulator notification** | M18 | Notify OSFI/SEC/PRA of new risk system |
| **Phase 4 complete** | M24 | Climate risk + CCAR + multi-region DR |
| **Decommission old system** | M26 | Legacy system turned off after parallel run |

---

## 9. Summary

> **What you built in 3 months would take a typical bank IT team 6-9 months just for Phase 0 (getting approval to start).**
>
> The full production system (all 10 sections from the design document) would take a bank team **18-24 months** with 4-6 people.
>
> The bottleneck is never the code — it's the compliance, procurement, and legacy integration overhead that defines bank IT velocity.
