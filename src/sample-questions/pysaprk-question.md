# PySpark Interview: 50 Most-Asked Questions With Senior-Level Answers

This sheet is for mid-senior and senior data-engineering interviews.
Each answer is phrased to sound like a hands-on senior PySpark engineer.

---

## 1) What is PySpark, and why use it instead of pandas?
**Senior answer (ready to say):** PySpark is the distributed execution layer I use when data volume, SLA, or concurrency outgrows a single machine. Pandas is still great for local profiling and notebook exploration, but production ETL needs Spark for horizontal scale, retry/fault tolerance, and scheduler-driven operations. Decision rule: use pandas for MB/GB local analytics; use Spark for cluster-scale, repeatable pipelines.

## 2) What are SparkContext and SparkSession?
**Senior answer (ready to say):** `SparkContext` is the low-level cluster interface; `SparkSession` is the modern unified API for DataFrame/SQL/catalog and internally manages the context. In production I initialize from `SparkSession.builder`, keep environment-specific configs explicit, and avoid hidden defaults between local/dev/prod to reduce drift.

## 3) What is the difference between RDD, DataFrame, and Dataset?
**Senior answer (ready to say):** RDD gives low-level control but less optimization. DataFrame is schema-aware and gets Catalyst + Tungsten optimizations, so it is the default for PySpark ETL. Dataset is typed for Scala/Java; in PySpark we usually model type safety through schema contracts and tests around DataFrames.

## 4) What are transformations and actions? Give examples.
**Senior answer (ready to say):** Transformations build lazy lineage (`filter`, `join`, `groupBy`) and actions trigger execution (`count`, `write`, `collect`). Senior practice is to minimize accidental actions in notebooks/jobs, because each action can recompute lineage and add cost. I place deliberate materialization boundaries where lineage or reuse justifies it.

## 5) What is lazy evaluation in Spark?
**Senior answer (ready to say):** Spark delays execution until an action so it can optimize the whole DAG end-to-end. That is why writing transformations in a clean chain matters; Spark can push filters down and prune columns more effectively. I only force materialization when I need checkpoints, caching, or a clear stage handoff.

## 6) Why avoid `collect()` in production?
**Senior answer (ready to say):** `collect()` brings all partitions to the driver, so it is a classic driver OOM and latency risk. In production I replace it with bounded patterns: `limit`, targeted aggregates, sampled debug outputs, or distributed writes. If I must collect, I enforce strict row caps and document why it is safe.

## 7) What is narrow vs wide transformation?
**Senior answer (ready to say):** Narrow transformations stay within partition lineage and are usually cheap; wide transformations trigger shuffle and dominate runtime cost. Senior tuning is mostly about reducing or reshaping wide stages, not micro-optimizing narrow ones.

## 8) Explain partitioning and why it matters.
**Senior answer (ready to say):** Partitions define parallelism and data movement. Too few partitions underutilize compute; too many create scheduler overhead and small-task inefficiency. I tune partitioning from Spark UI evidence (task time variance, spill, skew) instead of fixed folklore numbers.

## 9) `repartition()` vs `coalesce()`?
**Senior answer (ready to say):** `repartition()` reshuffles and rebalances; I use it before heavy joins/aggregations when balance matters. `coalesce()` is cheaper for reducing partitions near output writes. Practical pattern: rebalance for compute, coalesce for file layout.

## 10) What is shuffle and why is it expensive?
**Senior answer (ready to say):** Shuffle is cross-node redistribution and it is expensive because it combines network, disk spill, sort/merge, and serialization overhead. Senior optimization starts with reducing shuffled rows/columns early, then picking the right join strategy and partition plan.

## 11) What join types are commonly used in Spark?
**Senior answer (ready to say):** Inner/left/right/full are standard; `left_semi` and `left_anti` are high-value for existence filtering with lower payload cost. I use `left_anti` heavily for data-quality reconciliation and idempotent upsert staging.

## 12) What is broadcast join and when use it?
**Senior answer (ready to say):** Broadcast join replicates the small side to avoid shuffling the large side. It is ideal for stable dimension-to-fact enrichments when size assumptions are trustworthy. I always confirm the physical plan and monitor broadcast timeouts/memory, because forced hints can backfire.

## 13) How do you handle data skew in joins/groupBy?
**Senior answer (ready to say):** I prove skew first from stage/task outliers, then apply targeted fixes: salting hot keys, split-path processing, pre-aggregation, AQE skew handling, or selective repartitioning. The metric I care about is tail-task reduction (p95/p99) and lower spill, not just average task time.

## 14) What is AQE (Adaptive Query Execution)?
**Senior answer (ready to say):** AQE re-optimizes at runtime using actual shuffle stats, including partition coalescing, join strategy changes, and skew partition handling. It gives strong wins with little code change, but I still verify plans and metrics because AQE is not a substitute for bad data modeling.

## 15) `cache()` vs `persist()` vs `checkpoint()`?
**Senior answer (ready to say):** I use `cache()` for quick reuse, `persist()` for explicit storage levels on large intermediates, and `checkpoint()` to truncate long lineage when resiliency matters. Senior habit is to `unpersist()` aggressively and measure cache hit value versus executor memory pressure.

## 16) How do you choose number of partitions?
**Senior answer (ready to say):** I start from cluster capacity and data volume, then tune empirically from Spark UI. My target is balanced task duration with low spill and minimal stragglers, not a fixed magic number. Partition strategy is workload-specific and should be versioned with job configs.

## 17) Why prefer built-in functions over UDF?
**Senior answer (ready to say):** Built-ins stay inside optimized Spark execution and preserve Catalyst optimization opportunities. Python UDFs add JVM-Python serialization overhead and reduce planner visibility. My priority is built-in expressions first, pandas UDF second, regular Python UDF last.

## 18) What is pandas UDF, and when is it better?
**Senior answer (ready to say):** pandas UDF uses Arrow-based vectorized batches and is usually much faster than row-wise Python UDFs for custom logic. I use it when native Spark expressions cannot express the business rule. I validate Arrow compatibility, memory profile, and fallback behavior before production rollout.

## 19) How do you handle schema evolution and schema enforcement?
**Senior answer (ready to say):** I enforce explicit schemas for curated layers and allow controlled evolution through versioned contracts. New nullable columns are easier than type-breaking changes, which need migration strategy. I pair schema contracts with runtime data-quality checks and CI tests to prevent silent drift.

## 20) Parquet vs ORC vs CSV/JSON?
**Senior answer (ready to say):** For analytics, I standardize on columnar formats (Parquet/ORC, often Delta on Parquet) because of compression and pushdown benefits. CSV/JSON are usually raw ingestion or interchange formats, not efficient curated storage. The senior decision is separating raw compatibility from curated performance.

## 21) What is predicate pushdown and column pruning?
**Senior answer (ready to say):** Predicate pushdown filters at source read time; column pruning reads only needed fields. Together they reduce scan volume and downstream shuffle. I verify both in the physical plan and avoid early `select *` habits that block optimization.

## 22) How do you reduce small-file problems in data lakes?
**Senior answer (ready to say):** I manage output partitioning intentionally, avoid over-partitioning on high-cardinality keys, and schedule compaction/optimize jobs. Small-file control is an operational concern, so I track file-count and average-size trends as SLOs.

## 23) How do you make PySpark ETL idempotent?
**Senior answer (ready to say):** Idempotency comes from deterministic keys, dedup rules, and repeatable merge/overwrite semantics tied to stable input boundaries. Rerunning the same batch should reproduce the same output and reconciliation counts. I design this upfront, not as an afterthought.

## 24) How do you handle late-arriving data?
**Senior answer (ready to say):** I anchor logic on event time, define allowed lateness windows, and implement reconciliation/backfill paths. In streaming, that means watermarks and state policy; in batch, controlled correction windows with upserts. Business cutoff policy must be explicit and auditable.

## 25) How do you debug slow Spark jobs?
**Senior answer (ready to say):** My sequence is: inspect Spark UI for skew/spill/stragglers, inspect `explain("formatted")`, verify join and partition strategy, then benchmark one change at a time. I report improvement with stage-level evidence (task distribution, spill, shuffle bytes), not just total wall time.

## 26) What do executor memory and driver memory control?
**Senior answer (ready to say):** Driver memory covers planning/control and any driver-side materialization. Executor memory covers task execution, shuffle, and cache. Driver OOM often means accidental `collect`/`toPandas`; executor OOM usually indicates skew, oversized partitions, or poor cache strategy.

## 27) What are common Spark submit/deployment modes?
**Senior answer (ready to say):** Spark runs on local, standalone, YARN, Kubernetes, and managed services like Databricks. For production schedules, cluster deploy mode is usually more resilient because the driver is managed inside cluster infrastructure, not tied to a client session.

## 28) What are key Structured Streaming concepts?
**Senior answer (ready to say):** Core concepts are trigger model, checkpointing, state management, output mode, watermarks, and event-time windows. Exactly-once is achieved at system level: source guarantees + checkpoint integrity + idempotent sink semantics.

## 29) What is Delta Lake, and why use it with Spark?
**Senior answer (ready to say):** Delta adds ACID transactions, schema controls, time travel, and reliable merge semantics on lake storage. It reduces operational risk for CDC, incremental ETL, and replay workflows. In senior design, Delta is often the default curated-layer format for governance and recoverability.

## 30) How would you design a daily PySpark embedding ETL for thousands of funds?
**Senior answer (ready to say):** I split it into contract-driven ingestion, deterministic normalization, scalable chunk+embed compute, durable writes, and strong operations. Key controls are idempotent reruns by fund/date, retry isolation, lineage fields, and quality guardrails. Success metrics include SLA hit rate, bad-record rate, shuffle/spill profile, and cost per run.

## 31) How does Catalyst optimize queries beyond basic rule rewriting?
**Senior answer (ready to say):** Catalyst runs analysis, logical optimization, physical planning, and codegen phases; the biggest gains come from preserving optimizer visibility. UDF-heavy logic and stale stats reduce optimizer quality. I keep expressions planner-friendly and maintain stats where platform supports it.

## 32) What practical signs show whole-stage codegen helps or hurts?
**Senior answer (ready to say):** It helps when operators are simple and CPU-bound, reducing call overhead by operator fusion. It can hurt with overly complex expressions and codegen bloat. I decide from plan inspection plus runtime signals like GC pressure and stage regressions.

## 33) How are conflicting join hints resolved?
**Senior answer (ready to say):** Hints influence but do not override all planner constraints; invalid or conflicting hints can be ignored. I treat hints as surgical overrides and always validate the executed physical plan. If the data profile changes, I remove stale hints quickly.

## 34) Do bucketing and `sortWithinPartitions` still matter?
**Senior answer (ready to say):** Yes for repeated, stable key-based workloads where producer and consumer contracts are aligned. They can reduce shuffle/sort cost, but only if maintained consistently across the pipeline lifecycle. Without contract discipline, the operational complexity may outweigh benefit.

## 35) What is Dynamic Partition Pruning (DPP), and when does it fail?
**Senior answer (ready to say):** DPP prunes target partitions using runtime join filters, reducing scans significantly for partitioned tables. It fails when query shapes/predicates prevent planner insertion or required conditions are not met. I verify activation in plans rather than assuming it is on.

## 36) What are common window-function pitfalls at scale?
**Senior answer (ready to say):** Hidden full sorts and large state per partition are the main risks. Frame semantics errors (`rowsBetween` vs `rangeBetween`) can also break correctness subtly. I reduce input width first, define explicit partition keys, and benchmark memory/spill behavior.

## 37) Give a practical salting approach for skewed joins.
**Senior answer (ready to say):** For hot keys, add a salt bucket to the large side and replicate matching small-side keys across salt range, then join on key+salt. I start with small salt cardinality and tune by p95 task duration/spill reduction. Over-salting increases shuffle, so calibration matters.

## 38) How are bloom filters used in Spark pipelines?
**Senior answer (ready to say):** Bloom filters are probabilistic pre-filters to reduce scan/join volume before expensive stages. They trade tiny false-positive rates for major I/O savings on selective membership checks. I use them for performance acceleration, never as sole correctness logic.

## 39) What null-handling behaviors in joins/aggregations cause bugs?
**Senior answer (ready to say):** Null equality behavior in joins and aggregate null semantics (`count(col)` vs `count(*)`) are frequent root causes. I make null policy explicit in both design docs and test cases, especially for business keys and KPI calculations.

## 40) What should you inspect first in `explain` output?
**Senior answer (ready to say):** I check join strategy, `Exchange` nodes, and whether pushdown/pruning happened. Then I review broadcast decisions, partition counts, and AQE rewrites. Physical operators tell me where the real cost is.

## 41) Which runtime metrics best identify skew?
**Senior answer (ready to say):** I look at task runtime spread, skewed shuffle read bytes, spill concentration, and straggler counts in a stage. Large p95/p99 gaps versus median usually indicate skew. I use these to validate whether mitigation actually worked.

## 42) When should Kryo serialization be preferred?
**Senior answer (ready to say):** Kryo is preferable for shuffle/cache-heavy workloads where serialization cost is material. It performs best with class registration and compatibility checks. I roll it out with benchmarking, because serializer changes can expose edge-case regressions.

## 43) Is speculative execution always beneficial?
**Senior answer (ready to say):** No. It helps with transient node-level slowness, but not with deterministic data skew and can waste cluster resources. I enable it selectively and only after classifying the root cause of stragglers.

## 44) How do you handle broadcast timeout issues?
**Senior answer (ready to say):** I first validate if broadcast is still the right strategy; timeout tuning alone is not a long-term fix. Typical fixes are trimming broadcast payload columns, improving executor memory headroom, or switching join strategy.

## 45) What is a robust checkpoint-location strategy?
**Senior answer (ready to say):** Use durable storage with environment/job namespacing and access controls, separate from temporary staging paths. Add retention and cleanup policy to avoid orphaned state and storage bloat. Local checkpoint paths are not acceptable for resilient production restart.

## 46) How do you design safe incremental batch pipelines?
**Senior answer (ready to say):** I anchor increments on immutable high-water marks and keep replay-safe state. Late data follows explicit correction windows and merge logic. Design objective is deterministic recovery and auditability, not just speed.

## 47) What are key CDC + `MERGE` considerations in Spark/Delta?
**Senior answer (ready to say):** I enforce deterministic keys, event ordering semantics, and dedup before merge. Merge clauses must handle insert/update/delete plus late/out-of-order records. I monitor merge amplification and plan compaction cadence as part of operations.

## 48) What data-quality patterns work at Spark scale?
**Senior answer (ready to say):** I implement layered checks: schema, domain, referential, and distribution-drift thresholds. Bad records are quarantined with reason codes for reprocessing, unless strict SLA requires fail-fast. Data-quality metrics are published alongside business outputs.

## 49) What security/governance controls are expected in mature Spark platforms?
**Senior answer (ready to say):** Baseline controls are least privilege, encryption in transit/at rest, auditable lineage, and table/column-level access. Sensitive domains also need masking/tokenization and constrained debug workflows. Governance should be codified and enforced consistently across environments.

## 50) What should a production Spark runbook include?
**Senior answer (ready to say):** A runbook should map failures (OOM, skew, shuffle fetch, long GC, checkpoint issues) to exact triage actions and rollback/retry rules. It must include alert thresholds, escalation chain, and dashboard/log references. Strong runbooks are built for MTTR reduction.

---

## Senior interview delivery pattern (use this)
- `Decision:` what you choose in production.
- `Why:` tradeoff and risk.
- `Evidence:` Spark UI metric or SLA/cost metric.
- `Guardrail:` how you keep it safe in production.

Example: "We switched from sort-merge to broadcast join for a 30 MB dimension table, cut stage time 40%, and kept a size guardrail to avoid timeout regressions."

