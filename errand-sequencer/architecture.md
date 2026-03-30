# Errand Sequencer — System Design

## Overview

- **app/** — Streamlit frontend: chat, map, errand input.
- **agent/** — LangChain-style orchestration, memory, planning, prompts.
- **tools/** — Maps, weather, business hours; shared base utilities.
- **rag/** — Chunking, embeddings, ChromaDB retrieval, ingest script.
- **data/** — Raw docs, processed chunks, local Chroma persistence.
- **fine_tuning/** — Dataset prep, LoRA/QLoRA training, evaluation.
- **models/** — Local adapter weights under `fine_tuned/`.
- **configs/** — Central settings and logging configuration.

## Data flow (high level)

User input → agent orchestrator → tools + RAG retriever → planner → response and optional map updates.

This document is a stub; extend with diagrams and API contracts as the implementation solidifies.
