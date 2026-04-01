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

3. **Google Maps** (for LangChain tools: `get_hours`, `get_travel_time`, `get_directions`) — In [Google Cloud Console](https://console.cloud.google.com/apis/library), enable **Places API (New)**, **Distance Matrix API**, and **Directions API** on the project tied to your key. Billing must be on. Add to `.env` as a live line (no `#`):

   ```
   GOOGLE_MAPS_API_KEY=your_key_here
   ```

4. **Vector database (Chroma + embeddings)** — Knowledge lives under `data/raw/` (for example `data/raw/errand_tips/`). Ingest into Chroma, then the agent retrieves excerpts when `RAG_ENABLED=true`.

   **Chroma Cloud (recommended for access from anywhere)** — set in `.env`:

   ```
   CHROMA_MODE=cloud
   CHROMA_API_KEY=your_key_here
   CHROMA_TENANT=your_tenant_here
   CHROMA_DATABASE=your_database_here
   ```

   Re-ingest so data lands in that cloud project:

   ```bash
   python rag/ingest.py --reset
   ```

   **Local disk instead:** set `CHROMA_MODE=local` (or leave `CHROMA_MODE` unset and remove `CHROMA_API_KEY` for legacy behavior). Optionally override the folder with `CHROMA_DB_PATH` or `RAG_CHROMA_DIR`; default is `data/chroma_db/` (gitignored contents).

   ```bash
   python rag/ingest.py --reset
   ```

   **Sanity checks:** `python -m rag.diagnose` (connection mode + collection counts). For cloud retrieval smoke: `python tests/test_rag.py` from `errand-sequencer`. For pytest: `CHROMA_CLOUD_CHECK=1 pytest tests/test_rag.py -k chroma_cloud`.

   **Not seeing data in the Chroma dashboard?** If `diagnose` reports `local_persistent`, set `CHROMA_MODE=cloud` and credentials, reload `.env`, run `python -m rag.diagnose --clear-cache`, then ingest again. In the Cloud UI, open your org → the **database** that matches `CHROMA_DATABASE`, then **collections** — data is under `errand_knowledge` (override with `RAG_COLLECTION`).

## Run the app

```bash
cd errand-sequencer   # if you are not already here
source .venv/bin/activate
streamlit run app/main.py
```

Enter errands (e.g. one per line), click **Get suggestions**, and the UI calls your local Ollama model.

See `architecture.md` for system design.
