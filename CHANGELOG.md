# Changelog

All notable changes to the Customer Operations Control Tower, one phase at a time.

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