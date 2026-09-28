"""A local request trace containing an async model call."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from openai import AsyncOpenAI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field

from telemetry import setup

provider = setup("phoenix-part-01-fastapi")
tracer = trace.get_tracer(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncOpenAI() as client:
        app.state.model_client = client
        yield
    provider.force_flush()
    provider.shutdown()


app = FastAPI(lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)


@app.post("/chat")
async def chat(request: ChatRequest):
    model = os.environ["OPENAI_MODEL"]
    with tracer.start_as_current_span("answer-with-model") as span:
        span.set_attribute("openinference.span.kind", "LLM")
        span.set_attribute("llm.model_name", model)
        span.set_attribute("input.value", request.prompt)
        response = await app.state.model_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": request.prompt}],
        )
        answer = response.choices[0].message.content or ""
        span.set_attribute("output.value", answer)
    return {"answer": answer}
