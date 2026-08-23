# Azure Databricks Interview: 30 Most-Asked Questions With Senior-Level Answers

This sheet is for senior data engineer / data platform interviews.
Answers are phrased as practical, production-focused responses.

---

## 1) What is Azure Databricks, and when do you choose it?
**Senior answer (ready to say):** I choose Azure Databricks when I need a managed Spark platform with strong Lakehouse support, collaborative development, and enterprise controls. It reduces platform overhead versus self-managed Spark while giving rich optimization features (Delta, Photon, Auto Loader, Workflows). For data products with strict SLAs and mixed batch/streaming needs, it is usually my default.

## 2) How do you design a Databricks workspace strategy for enterprise scale?
**Senior answer (ready to say):** I separate workspaces by environment and sometimes by domain (for example, `dev/test/prod` and high-regulated domains). I keep identity, networking, and secret boundaries explicit to avoid cross-env blast radius. Governance is centralized via Unity Catalog, but runtime isolation stays environment-specific.

## 3) Clusters vs SQL Warehouses vs Serverless: how do you decide?
**Senior answer (ready to say):** I map compute to workload profile. All-purpose or job clusters for Spark ETL/ML code paths, SQL Warehouses for BI/SQL workloads, and serverless options for fast startup and elastic analytics when policy allows. Decision factors are concurrency, latency SLA, operational overhead, and unit cost.

## 4) What are cluster policies and why are they critical?
**Senior answer (ready to say):** Cluster policies enforce guardrails: node types, autoscaling bounds, runtime versions, tags, and security settings. They prevent cost sprawl and insecure cluster patterns. In mature teams, policies are mandatory and aligned to workload classes (etl, ad-hoc, ml, prod-critical).

## 5) What are cluster pools and when do you use them?
**Senior answer (ready to say):** Pools reduce startup latency by keeping warm VM capacity. I use them for frequent short jobs where spin-up delay affects SLA and cost. For long-running workloads, pool benefits are smaller; I validate with queue time and cluster start metrics.

## 6) How do you manage code in Databricks for CI/CD?
**Senior answer (ready to say):** I treat notebooks as thin orchestration and keep core logic in tested Python packages/modules. I use Databricks Repos with Git branches, CI tests in pipelines, and promotion by environment-specific deployment jobs. Production releases are versioned and rollbackable.

## 7) Unity Catalog vs legacy Hive metastore: key differences?
**Senior answer (ready to say):** Unity Catalog gives centralized governance across workspaces with fine-grained permissions on catalogs/schemas/tables/views/functions and better lineage/audit integration. Hive metastore is less centralized and harder to govern at enterprise scale. For regulated data platforms, Unity Catalog is the preferred operating model.

## 8) How do you implement data governance in Unity Catalog?
**Senior answer (ready to say):** I implement least-privilege RBAC at catalog/schema/table levels, standardize ownership groups, and enforce naming/lifecycle conventions. For sensitive fields, I use masking patterns and controlled views. Governance is codified and reviewed like application code.

## 9) What is your medallion architecture approach in Databricks?
**Senior answer (ready to say):** Bronze stores raw immutable ingestion with full lineage. Silver applies schema enforcement, dedup, and business normalization. Gold serves curated, consumption-ready aggregates for BI/ML. This separation gives clear accountability, replay paths, and quality gates.

## 10) Why Delta Lake is foundational in Databricks?
**Senior answer (ready to say):** Delta gives ACID transactions, schema controls, time travel, and efficient `MERGE`/upsert semantics on cloud object storage. It turns lake storage into a reliable table layer for production ETL. It is essential for CDC, backfills, and auditable reruns.

## 11) How do you optimize Delta tables in production?
**Senior answer (ready to say):** I tune partition strategy carefully, avoid over-partitioning, run file compaction (`OPTIMIZE` where applicable), and manage retention/vacuum policies. I monitor file counts, query scan size, and write amplification. Performance tuning is tied to workload access patterns, not generic defaults.

## 12) What is Delta Live Tables (DLT) and when do you use it?
**Senior answer (ready to say):** DLT is managed pipeline orchestration for declarative ETL with built-in quality expectations, lineage, and operational controls. I use it when team productivity and standardized operations are more important than fully custom orchestration. For highly specialized control planes, I may keep custom Spark + Workflows.

## 13) How do you design Databricks Workflows for reliability?
**Senior answer (ready to say):** I model jobs as small, composable tasks with explicit dependencies and retry policies. I isolate failure domains by dataset/partition where possible, avoid giant monolithic tasks, and push idempotent write design into each step. Alerting and runbook links are attached at workflow level.

## 14) How do you do parameterization across environments?
**Senior answer (ready to say):** I externalize environment config (catalog names, storage paths, secrets scopes, feature flags) and inject via job parameters or config files. Code stays constant across environments; only deployment/config changes. This reduces drift and improves reproducibility.

## 15) How do you handle secrets and credentials in Azure Databricks?
**Senior answer (ready to say):** I avoid hardcoded credentials and use secret scopes with Azure Key Vault-backed integration where possible. Access is granted by least privilege and audited. For storage/service auth, managed identity or service principal patterns are preferred over shared keys.

## 16) Explain managed identity usage with Databricks on Azure.
**Senior answer (ready to say):** Managed identity removes secret rotation burden and improves security posture by using Azure AD-issued tokens. I assign RBAC roles at minimal scope (for example, storage container path). This is my preferred auth path for production data access in Azure-native setups.

## 17) How do you secure networking for Databricks (VNet, Private Link)?
**Senior answer (ready to say):** I deploy with VNet injection and private endpoints for control/data plane integration where required by policy. I restrict public egress, define NSG rules explicitly, and route outbound traffic through approved controls. Security architecture is validated with platform/network teams before go-live.

## 18) How do you approach Photon adoption?
**Senior answer (ready to say):** Photon can significantly improve SQL/DataFrame performance for supported workloads. I enable it by policy for suitable jobs, benchmark representative pipelines, and monitor cost/performance ratio. If workload characteristics are unsupported or gains are minimal, I keep standard runtime.

## 19) How do you tune Spark jobs in Databricks beyond basic config tweaks?
**Senior answer (ready to say):** I start with query plan and Spark UI evidence: shuffle hotspots, skew, spill, and join strategy. Then I optimize data layout, projection/filter pushdown, partition strategy, and join method before touching low-level configs. Tuning is evidence-driven and regression-tested.

## 20) How do you handle skewed data in Databricks pipelines?
**Senior answer (ready to say):** I identify skew from stage/task outliers, then apply targeted fixes: salting hot keys, split pipelines for heavy keys, AQE skew handling, and pre-aggregation. I evaluate success by p95/p99 task duration and spill reduction, not only wall-clock averages.

## 21) How do you optimize costs in Databricks?
**Senior answer (ready to say):** Cost control combines right-size clusters, autoscaling bounds, auto-termination, workload-specific policies, and storage layout optimization. I track cost per successful run and per TB processed, not just monthly totals. Governance tags and chargeback/showback are mandatory at enterprise scale.

## 22) What is your observability strategy for Databricks jobs?
**Senior answer (ready to say):** I combine native run logs, Spark UI metrics, Delta table history, and cloud monitoring dashboards. For each pipeline I track SLA, data volume, quality failures, and compute efficiency metrics. Alerts are actionable and linked to runbook steps.

## 23) How do you handle schema drift with Auto Loader?
**Senior answer (ready to say):** I use schema inference for controlled discovery, then enforce explicit schema and evolution rules for curated layers. Auto Loader + schema location simplifies incremental file ingestion, but governance still requires contract checks and quarantine for unexpected fields.

## 24) How do you design streaming pipelines in Databricks?
**Senior answer (ready to say):** I design around event time, checkpoint durability, and idempotent sink writes. Bronze streaming ingestion is append-focused; Silver applies dedup/watermark logic; Gold serves business aggregates. The key is restart safety and deterministic behavior under late/out-of-order data.

## 25) How do you ensure idempotency in Databricks ETL jobs?
**Senior answer (ready to say):** I enforce deterministic keys, stable batch boundaries, and merge/upsert semantics instead of blind append. Reruns for same input range must produce identical outputs and reconciliation totals. Idempotency is validated in both QA tests and operational runbooks.

## 26) How do you perform CDC ingestion into Delta tables?
**Senior answer (ready to say):** I stage CDC events with ordering metadata, deduplicate by business key + event version, then apply `MERGE` with explicit insert/update/delete logic. I also handle late and out-of-order changes with correction windows. Operationally, I monitor merge amplification and compaction cadence.

## 27) What is your approach to DR (disaster recovery) in Databricks?
**Senior answer (ready to say):** DR plan covers metadata/governance, data replication strategy, infra-as-code redeploy, and tested failover runbooks. RTO/RPO targets drive architecture choices (cross-region storage replication, catalog backup/export strategy). DR is only real if rehearsed periodically.

## 28) How do you troubleshoot “job succeeds but data is wrong” incidents?
**Senior answer (ready to say):** I trace lineage from output back to source snapshots, compare row-level reconciliation, and inspect schema/null/key drift first. Then I validate join logic, dedup keys, and watermark/cutoff assumptions. I prefer fast containment (quarantine/revert) before deep root-cause finalization.

## 29) What are common Databricks anti-patterns you avoid?
**Senior answer (ready to say):** Giant monolithic notebooks, ad-hoc mutable schemas in curated layers, uncontrolled `collect()` usage, over-partitioned small files, and no environment policy controls. These create fragility, runaway costs, and hard-to-debug incidents. I enforce standards early to avoid debt.

## 30) If you join a new team, what first 30-day Databricks improvements do you prioritize?
**Senior answer (ready to say):** I baseline platform health first: failed-job taxonomy, top-cost jobs, top-latency jobs, and governance gaps. Then I implement quick wins: cluster policies, job retries/timeouts, table optimization cadence, and observability SLIs. The goal is immediate stability plus a roadmap for scale.

---

## Senior interview delivery pattern (recommended)
- `Decision:` what you choose in production.
- `Tradeoff:` what you give up and why it is acceptable.
- `Evidence:` metric (SLA, p95 duration, spill, cost/run, failed-run rate).
- `Guardrail:` policy/control to keep it safe.

Example: "We moved high-frequency ETL jobs to pooled job clusters, reduced startup latency by 35%, and enforced cluster policies to prevent oversized node selection."

