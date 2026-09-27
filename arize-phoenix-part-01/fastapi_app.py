"""Local teaching service. Run with uvicorn fastapi_app:app."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from openai import AsyncOpenAI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field

from telemetry import setup

# Create one tracing provider for this application process.
provider = setup("phoenix-part-01-fastapi")
tracer = provider.get_tracer(__name__)


# FastAPI runs this startup/shutdown manager for the application.
@asynccontextmanager
async def lifespan(app):
    app.state.model = os.environ["OPENAI_MODEL"]
    try:
        # Reuse one asynchronous client rather than creating a client per request.
        async with AsyncOpenAI(timeout=30.0, max_retries=1) as client:
            app.state.client = client
            # Serve requests here; execution resumes below when the app shuts down.
            yield
    finally:
        # Flush buffered telemetry during shutdown, then release exporter resources.
        provider.force_flush()
        provider.shutdown()


app = FastAPI(lifespan=lifespan)
# Create HTTP request spans and extract incoming trace context automatically.
FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)


# Validate incoming JSON before calling the model.
class ChatRequest(BaseModel):
    # Reject empty prompts and limit the size of this demonstration input.
    prompt: str = Field(min_length=1, max_length=2000)


# Handle a POST request sent to /chat.
@app.post("/chat")
async def chat(body: ChatRequest):
    # This model operation becomes a child of the active HTTP request span.
    with tracer.start_as_current_span("answer-with-model") as span:
        span.set_attribute("openinference.span.kind", "LLM")
        span.set_attribute("input.value", body.prompt)
        span.set_attribute("llm.model_name", app.state.model)
        # await lets the server do other work while the model request is in flight.
        response = await app.state.client.chat.completions.create(
            model=app.state.model,
            messages=[{"role": "user", "content": body.prompt}],
        )
        text = response.choices[0].message.content or ""
        # Record the answer for inspection; this does not grade its correctness.
        span.set_attribute("output.value", text)
        return {"answer": text}
