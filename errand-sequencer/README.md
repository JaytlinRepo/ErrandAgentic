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

4. **RAG (Chroma + embeddings)** — Knowledge lives under `data/raw/` (sample tips in `data/raw/errand_tips/`). Ingest into a vector store, then the agent retrieves excerpts automatically.

   **Local Chroma (default):** embeddings + DB under `data/chroma_db/` (gitignored contents).

   ```bash
   python -m rag.ingest --reset
   ```

   **Chroma Cloud:** add your API key to `.env` (and optional tenant/database from the Chroma dashboard):

   ```
   CHROMA_API_KEY=ck-your-key-here
   # Optional if not auto-resolved from the key:
   # CHROMA_TENANT=your-tenant-id
   # CHROMA_DATABASE=your-database-name
   ```

   Then run `python -m rag.ingest --reset` again so data is written to the cloud project.

   **Not seeing data in the Chroma dashboard?** Run `python -m rag.diagnose` from `errand-sequencer/`. If it says `local_persistent`, your API key was not loaded — fix `.env` (variable name `CHROMA_API_KEY`) and re-run ingest. In the Cloud UI, open your **organization → Database** (match `CHROMA_DATABASE` if set), then **Collections** — data is under the collection name `errand_knowledge` (configurable via `RAG_COLLECTION`), not as separate “databases” per markdown file.

## Run the app

```bash
cd errand-sequencer   # if you are not already here
source .venv/bin/activate
streamlit run app/main.py
```

Enter errands (e.g. one per line), click **Get suggestions**, and the UI calls your local Ollama model.

See `architecture.md` for system design.
