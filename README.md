# CLO Memo Extractor

Extract structured data from CLO (Collateralized Loan Obligation) surveillance /
refi memos using an LLM, with a Streamlit web UI.

## Features
- **Flexible Extraction Engines**:
  - 🤖 **AI LLM Agent** (OpenRouter, Gemini, Groq) with automatic fallback.
  - ⚡ **Standalone Offline Engine** (100% offline rule-based extraction; zero API keys required).
- Upload a memo (`.txt` / `.md` / `.pdf`), paste text, or fetch via URL.
- **CLO Committee Prep Studio**: Instantly generate executive CLO Committee Memorandums, refinancing briefs, and action item lists for investment committees.
- Download results as JSON, Excel (`.xlsx`), Markdown (`.md`), or plain text (`.txt`).

## Local run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="..."      # or GROQ_API_KEY / OPENROUTER_API_KEY
streamlit run app.py
```
Open http://localhost:8501

The provider API keys are read from `.streamlit/secrets.toml` (gitignored)
or from environment variables. The sidebar key field is left blank and only
used to *override* the stored key — the real key is never shown in the UI.

## Deploy to Streamlit Cloud
1. Push this repo to GitHub.
2. Go to https://share.streamlit.io → **New app** → pick the repo, entrypoint `app.py`.
3. **App settings → Secrets**, paste:
   ```toml
   OPENROUTER_API_KEY = "sk-or-v1-..."
   GEMINI_API_KEY = "AIza..."
   GROQ_API_KEY = "gsk_..."
   CLO_MODEL = "qwen/qwen3.8-27b"
   ```
4. Deploy. The app reads these secrets at runtime.

## CLI usage
```bash
export GROQ_API_KEY="..."
python3 clo_extractor.py          # reads sample_clo_memo.txt
```

## Default models per provider
| Provider    | Default model            | Base URL |
|-------------|--------------------------|----------|
| openrouter  | z-ai/glm-5.3-flash       | openrouter.ai/api/v1 |
| gemini      | gemini-2.5-flash         | generativelanguage.googleapis.com/v1beta/openai |
| groq        | qwen/qwen3.8-27b         | api.groq.com/openai/v1 |

Note: OpenRouter requires sufficient account credits to return a full CLO JSON
(the response is large). Gemini and Groq work on their free tiers.
