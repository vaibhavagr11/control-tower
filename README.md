# Customer Operations Control Tower

An AI-native operations layer that shifts customer support from reactive to
proactive, autonomous resolution. Built iteratively, one phase at a time.

## Phases
- **Phase 0 — Foundations:** operational data layer + policy repository (mocked)
- **Phase 1 — Reactive Resolution Copilot:** classify → retrieve → recommend,
  human-in-the-loop *(current)*
- Phase 2+ — orchestration, learning, prediction, prevention

## Stack
Python · LangChain (LCEL) · Pydantic structured output · LangSmith tracing · uv

## Setup
```bash
uv sync
cp .env.example .env   # add your OPENAI_API_KEY
```