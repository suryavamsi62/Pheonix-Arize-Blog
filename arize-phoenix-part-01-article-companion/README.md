# Part 1 companion code

These examples match [the article](../../Your-Agent-Returned-200-OK-Part-1.md). They use synthetic policy and order data. Model calls use your OpenAI API key and may incur charges.

The examples read `OPENAI_API_KEY` and `OPENAI_MODEL` from this folder's `.env` file. Replace the invalidated key there with a new valid key. The file is ignored by Git; keep it private.

Use Python 3.11 or newer. Check the current Phoenix release's Python requirement before installing.

## Start Phoenix (Terminal 1)

Windows PowerShell:

```powershell
python -m venv .phoenix-venv
.\.phoenix-venv\Scripts\Activate.ps1
python -m pip install arize-phoenix
phoenix serve
```

macOS or Linux:

```bash
python3 -m venv .phoenix-venv
source .phoenix-venv/bin/activate
python -m pip install arize-phoenix
phoenix serve
```

Open <http://localhost:6006> and leave the server running.

## Install and run examples (Terminal 2)

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env with your valid key and model before running the examples.
python plain_python.py
python langgraph_example.py
uvicorn fastapi_app:app --host 127.0.0.1 --port 8000
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
test -e .env || cp .env.example .env
# Edit .env with your valid key and model before running the examples.
python plain_python.py
python langgraph_example.py
uvicorn fastapi_app:app --host 127.0.0.1 --port 8000
```

The `.env` values take precedence over older terminal variables. The selected model must support Chat Completions and tool calling. Use `http://127.0.0.1:8000/docs` to try the FastAPI route. Each example writes to its own project in Phoenix. Set `PHOENIX_COLLECTOR_ENDPOINT` in `.env` to another full HTTP trace URL if needed.

The LangGraph example uses a direct OpenAI call inside a graph node. Its graph nodes are instrumented through the LangChain integration; provider-specific model details are not automatically captured by that integration. The Python and FastAPI examples attach model attributes manually.
