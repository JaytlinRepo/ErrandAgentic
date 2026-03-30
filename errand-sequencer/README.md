# Errand Sequencer

Agentic errand sequencing with a Streamlit UI, RAG, and optional fine-tuning.

## Setup

1. **Ollama** — Install and start [Ollama](https://ollama.com), then pull a model (defaults to `llama3.2:latest`):

   ```bash
   ollama pull llama3.2
   ```

2. **Python** — From this directory:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   Optional: copy `.env` and set `OLLAMA_HOST` / `OLLAMA_MODEL` if you use a non-default host or tag.

## Run the app

```bash
cd errand-sequencer   # if you are not already here
source .venv/bin/activate
streamlit run app/main.py
```

Enter errands (e.g. one per line), click **Get suggestions**, and the UI calls your local Ollama model.

See `architecture.md` for system design.
