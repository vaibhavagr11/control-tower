# Changelog

All notable changes to the Customer Operations Control Tower, one phase at a time.

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
- Hybrid keyword + semantic retrieval (EnsembleRetriever with BM25) — adds lexical matching alongside dense
- Experiment: upgrade embedding model (bge-small / gte-small) + re-index — bi-encoder is the recall limiter; optional since rerank fixes ordering
- Verifiable source tracking (retrieved_sources on CopilotResult) — needed before Phase 2 autonomy
- RAG fallback: cascading retrieval (relaxed retry before escalating); never fall back to ungrounded model knowledge
- LLM resilience: .with_retry() for transient rate limits, .with_fallbacks() to a backup model
- Header-aware chunking (UnstructuredPDFLoader + MarkdownHeaderTextSplitter) to keep related rules in one chunk
- Migrate off deprecated langchain-community PyPDFLoader
- pytest tests: guardrail, retrieval, accuracy()
- Phase 2: orchestration engine + specialized agents + scoped autonomy