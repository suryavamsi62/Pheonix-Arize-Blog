# Arize Phoenix Part 1 examples

Companion to **Your Agent Returned 200 OK. Did It Actually Do the Job?**

## Setup

Use Python 3.11 or newer for the examples and check the Python requirements of the Phoenix release you install. Draft 2 uses a separate server environment in Terminal 1:

```powershell
# Install the server separately from the application dependencies.
python -m venv .phoenix-venv
.\.phoenix-venv\Scripts\Activate.ps1
python -m pip install arize-phoenix
# Keep this terminal running while trying the examples.
phoenix serve --host 127.0.0.1 --port 6006
```

On macOS/Linux activate with `source .phoenix-venv/bin/activate`. Open http://localhost:6006. Alternatively, use `uvx arize-phoenix serve --host 127.0.0.1 --port 6006` if uv is installed.

For Docker, use the included `compose.yaml` and `docker compose up -d`. Do not run it alongside another Phoenix server on port 6006. `docker compose logs phoenix` shows startup output; `docker compose down` stops the container and preserves its named volume. This Compose configuration is for local learning, not a complete production deployment.

In Terminal 2, from this folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "your-accessible-chat-model"
```

On macOS/Linux, activate with `source .venv/bin/activate` and use `export OPENAI_API_KEY=...` and `export OPENAI_MODEL=...`.

Select a Chat Completions model supporting tool calling. API calls incur provider charges. Use synthetic prompts: the examples export inputs and outputs to your local Phoenix server. Never commit credentials. Optionally set `PHOENIX_COLLECTOR_ENDPOINT` to an HTTP OTLP trace endpoint; the default is `http://localhost:6006/v1/traces`. These instructions cover local Phoenix only.

## Run

```sh
python plain_python.py
python langgraph_example.py
uvicorn fastapi_app:app --host 127.0.0.1 --port 8000
```

Run each separately. For the web example, use http://localhost:8000/docs to submit a POST to `/chat`.

| Script | Phoenix project | Inspect |
| --- | --- | --- |
| plain_python.py | phoenix-part-01-python | A CHAIN parent, RETRIEVER and LLM children, document contents and answer |
| langgraph_example.py | phoenix-part-01-langgraph | Model calls, tool arguments/results, bounded graph execution |
| fastapi_app.py | phoenix-part-01-fastapi | Incoming request and child model span |

The Python retrieval and order lookup are fixed fixtures, not a vector search engine or live order service. The Python workflow is deterministic orchestration around a real model call. The LangGraph example lets the model choose tool calls. The FastAPI example is an independent minimal endpoint.

## Troubleshooting

- No traces: ensure Phoenix is running, check the collector endpoint, and allow exports to finish.
- Authentication/model errors: verify your provider key, model access, and Chat Completions/tool support.
- Graph recursion error: inspect repeated tool calls in Phoenix; do not blindly raise the limit.
- Port in use: stop the existing service or choose another port and update the endpoint.

## Validation status

Dependencies are intentionally unpinned until a full integration run establishes a tested set. Do not interpret this as a reproducible production environment. Python syntax checks passed. Draft 2 adds comments without changing the Python executable syntax trees. Live model calls, Docker startup, and Phoenix UI ingestion have not been verified.

## Repository publication

Approved public repository target: `suryavamsi62/arize-phoenix-part-01`. Publication remains pending GitHub sign-in. The article currently links to this local companion folder. Once published, replace that link with the verified repository URL.
