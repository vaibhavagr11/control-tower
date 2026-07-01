# Changelog

All notable changes to the Customer Operations Control Tower, one phase at a time.

## [Phase 2.2] - LangGraph Checkpointers
### Added
- `langgraph-checkpoint-sqlite` dependency
- `copilot/checkpointer.py`: shared `SqliteSaver` instance backed by `data/control_tower.db` with `check_same_thread=False` for multi-call use
- Graph compiled with checkpointer: every node's output is automatically persisted to SQLite after each run — no manual state management
- `recommend()` in `copilot.py` passes `config={"configurable": {"thread_id": ticket_id}}` on every `graph.invoke()` — each ticket is a persistent, replayable thread
- `recommend_graph.get_state(config)` confirmed returning all 15 state fields after a run
### Notes / learnings
- `next: ()` (empty tuple) from `get_state()` confirms the graph ran to `END` cleanly — non-empty `next` would indicate an interrupted graph waiting for human input (the pattern we'll use in Phase 2.3 for assisted tickets)
- LangGraph emits deserialization warnings for unregistered Pydantic types (`IssueClassification`, `ResolutionRecommendation`) when reading checkpoints — non-breaking in current version; proper fix is registering schemas with msgpack at config level, deferred to production hardening phase
- `storage.py` conversation/customer history functions are now superseded by the checkpointer for graph state persistence; kept for feedback log which is not part of graph state

## [Phase 2.1] - Tool Layer & Copilot Refactor
### Added
- `tools/` package: `oms.py`, `carrier.py`, `payment.py`, `data.py`
- OMS tools: `lookup_order`, `lookup_orders_by_customer`, `cancel_order`, `create_replacement_order` (with `item_skus` and `company`/`customer_exchange` reason type)
- Carrier tools: `get_tracking_status`, `generate_return_label` (prepaid for company fault, customer-pays instructions for customer reason)
- Payment tool: `process_refund` with `standard` (return required) and `forced` (no return required) types; idempotency guard via `REFUND_LOG`
- Uniqlo-realistic mock data: multi-item clothing orders with SKU/size/color/qty/unit_price, customer profiles with `return_history` and `order_history`, carrier tracking event logs
- Return reason logic: `company` fault (wrong item, damaged, not received) → prepaid label + forced refund; `customer` reason (changed mind, wrong size) → customer pays return + standard refund
- `create_replacement_order` handles both free company replacements and charged customer exchanges; operates on specific `item_skus` not the whole order
### Changed
- `copilot/` refactored into `nodes/` package — one file per cognitive responsibility: `triage.py`, `investigation.py`, `policy.py`, `resolution.py`, `communication.py`, `escalation.py`, `actions.py`, `clarification.py`
- `graph.py` reduced to wiring only (~50 lines); `state.py` and `routing.py` extracted as standalone modules
- `investigation_node` now calls `lookup_order` tool instead of `retrieve_context` from mock_store
- Action nodes derive `return_reason_type` from `classification.issue_type`; `item_skus` default to all SKUs in the order
- `_determine_autonomy_tier` now computes `account_age` from `member_since` date string instead of a pre-stored field
- `offer_compensation` removed from action routing — compensation maps to `issue_refund` at resolver level (loyalty system removed)
### Notes / learnings
- Tool interface (input/output schema) is the stable contract across enterprises — the implementation behind each tool changes per client; this is how Decagon ships the same agent to different retailers
- Return reason type (`company` vs `customer`) is derived deterministically from `classification.issue_type` — keeps the decision auditable and out of the LLM's hands
- `action_router_node` returning `{}` (no state update) is represented as `None` in LangGraph's stream output — requires `outputs = outputs or {}` guard

## [Phase 1.4] - Memory
### Added
- Conversation memory: per-ticket chat history (`conversation_history`) threaded into both `classify_chain` and `resolve_chain` via `MessagesPlaceholder("chat_history")`
- Multi-session memory: per-customer history across tickets (`customer_memory`), keyed off the `customer_id` resolved from the order, formatted and threaded into the resolver prompt
- Windowed memory: `trim_messages(strategy="last", max_tokens=6, token_counter=len, start_on="human")` caps how much raw history reaches the model regardless of how long a ticket thread runs
- Summary memory: messages that age out of the window are condensed by a small summarizer chain into a one-line `SystemMessage`, so early facts/constraints survive even once the raw turns are dropped
- Persistent memory (`copilot/storage.py`): SQLite-backed store (`data/control_tower.db`) for conversation history, customer memory, and the feedback ledger — `ResolutionCopilot` hydrates from disk on construction and writes through on every update, so state survives a restart
### Notes / learnings
- Confirmed `RunnableWithMessageHistory` is deprecated in the pinned `langchain_core` (1.4.8) in favor of LangGraph persistence by reading the installed source directly; built memory as plain dict/SQLite state + `MessagesPlaceholder` instead of adopting it
- Multi-session memory's fraud-risk signal from repeat claims is wired correctly (verified via direct prompt rendering) but the model doesn't reliably weight repeated identical issue types as a fraud signal under `reasoning_effort="low"` — prompt tuning deferred, tracked in backlog
- Summary memory recomputes the summary fresh from whatever's currently outside the window on every call, rather than incrementally caching it — simpler, at the cost of a small repeated LLM call once a ticket runs long

## [Phase 1.3] - Retrieval Scale, Hybrid Search & Evaluation
### Added
- Corpus expanded from 3 to 25 policy PDFs via `scripts/generate_policies.py` + `catalog.json`, then regenerated as enterprise-length manuals (3-20 pages each, 199pp total) to stress-test chunking/retrieval at realistic scale
- Hybrid retrieval: `BM25Retriever` (lexical) fused with the multi-query dense retriever via `EnsembleRetriever`
- Eval harness (`scripts/eval_retrieval.py` + `evals/retrieval_cases.json`): recall@1/recall@3/MRR across semantic/exact/ambiguous query types, a context-completeness check (does the retrieved text actually contain the cited rule), and junk no-match accuracy
- Parent-child chunking (`policies/ingest.py`): 600-char child chunks for precise retrieval, mapped to 3500-char parent chunks (`.parent_docstore.json`/`.child_docstore.json`) so the resolver gets full context instead of a narrow fragment
### Changed
- `retrieve_policy_docs`: retrieve on child chunks (k boosted to `max(k*8, 24)` candidates) → map to parent chunks → cross-encoder rerank and gate on the parents, replacing the earlier rerank-children-directly approach
- Relevance gate moved from the embedding-similarity threshold to a cross-encoder score threshold (`RERANK_SCORE_MIN = -8.0`) on the hybrid+reranked results — BM25 always returns its top-k, so the embedding threshold alone could no longer act as the "no match" safety net
- Hybrid fusion weights tuned from 0.5/0.5 (BM25/dense) to 0.4/0.6 after measuring against the eval set
### Notes / learnings
- BM25 closed a real blind spot dense-only retrieval had on exact codes/IDs (POL-CX-022, ERR-PAY-002), but it always returns *something* regardless of relevance, which reintroduced false positives on junk queries — the cross-encoder gate restored the original "no matching policy" behavior
- Retrieving on small child chunks improved match precision, but a child chunk alone sometimes didn't contain the full rule text; returning its parent chunk instead fixed context completeness without giving up that precision

## [Phase 1.2] - Advanced Retrieval
### Added
- Scored retriever: as_retriever(search_type="similarity_score_threshold"), calibrated threshold 0.30 — escalates on no-match instead of returning irrelevant policy
- Metadata filtering: status="active" hard constraint (optional policy_type); richer chunk metadata (doc_id, policy_type, version, status); citations now use doc_id
- Cosine distance for the Chroma collection (clean 0–1 relevance scores)
- Multi-query retrieval (MultiQueryRetriever): LLM rephrases the query to broaden recall
- Two-stage retrieval: contextual compression with a cross-encoder reranker (CrossEncoderReranker + HuggingFaceCrossEncoder ms-marco-MiniLM-L-6-v2, top_n=3)
### Changed
- retrieve_policies pipeline is now: multi-query → bi-encoder retrieve (threshold + filter) → cross-encoder rerank
### Notes / learnings
- Bi-encoder (all-MiniLM-L6-v2) mis-ranked the delay policy above refund (0.305 vs 0.294); the cross-encoder corrected ordering — the limit was the bi-encoder *architecture*, not model size
- Tried LLMChainExtractor first: over-compressed and dropped REPLACE-PREFERRED, breaking T-1. EmbeddingsFilter (drops whole chunks) was safer; cross-encoder rerank was best. Lesson: extract-compressors risk losing signal; filter/rerank compressors don't

## [Phase 1.1] - Policy RAG
### Added
- PDF policy documents + ingestion pipeline (load → chunk → embed → Chroma)
- Local sentence-transformers embeddings (no API key)
- Semantic policy retrieval replacing the hardcoded rules dict

## [Phase 1] - Reactive Resolution Copilot
### Added
- Pydantic schemas: IssueClassification, ResolutionRecommendation, CopilotResult
- Mock operational data layer (customers, orders) + structured policy repository
- Config module (OpenRouter provider, GPT-5.4 nano/mini, guardrail thresholds)
- Classify LCEL chain (gpt-5.4-nano) and resolve LCEL chain (gpt-5.4-mini)
- Deterministic human-approval guardrail (value, fraud signals, confidence)
- Copilot orchestrator: classify → retrieve context → retrieve policy → resolve → gate
- Human-in-the-loop feedback ledger with acceptance-rate metric
- LangSmith tracing via @traceable across the pipeline
- End-to-end demo runner (scripts/demo_phase1.py)

## [Phase 0] - Foundations
### Added
- Project scaffold: uv package, src/ layout, secrets hygiene
- Git repository, branch-per-phase workflow, GitHub remote

## Backlog (deferred, with rationale)
- Experiment: upgrade embedding model (bge-small / gte-small) + re-index — bi-encoder is the recall limiter; optional since rerank fixes ordering
- Verifiable source tracking (retrieved_sources on CopilotResult) — needed before Phase 2 autonomy
- RAG fallback: cascading retrieval (relaxed retry before escalating); never fall back to ungrounded model knowledge
- LLM resilience: .with_retry() for transient rate limits, .with_fallbacks() to a backup model
- Header-aware chunking (UnstructuredPDFLoader + MarkdownHeaderTextSplitter) to keep related rules in one chunk — partially covered by parent-child chunking (Phase 1.3), but that's size-based, not header-aware
- Migrate off deprecated langchain-community PyPDFLoader
- pytest tests: guardrail, retrieval, accuracy()
- Prompt tuning: have the resolver weight repeat identical-issue-type claims from customer_history as a stronger fraud signal (currently wired but under-weighted at reasoning_effort="low")
- Incremental/cached summary memory, instead of resummarizing the full overflow on every call
- Phase 2: orchestration engine + specialized agents + scoped autonomy