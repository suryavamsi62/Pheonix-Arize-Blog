"""A fixed retrieve-then-answer workflow with explicit spans."""

import json
import os

from openai import OpenAI
from opentelemetry import trace

from telemetry import setup

DOCUMENTS = [
    {
        "id": "ordinary-returns",
        "content": "Undamaged items may be returned within 30 days of delivery.",
    },
    {
        "id": "damaged-deliveries",
        "content": "Damage must be reported within 48 hours of delivery. Contact support with photos of the damaged item and packaging.",
    },
]


def answer(question: str, tracer, client: OpenAI, model: str) -> str:
    with tracer.start_as_current_span("support-workflow") as workflow:
        workflow.set_attribute("openinference.span.kind", "CHAIN")
        workflow.set_attribute("input.value", question)

        with tracer.start_as_current_span("retrieve-policy") as retrieval:
            retrieval.set_attribute("openinference.span.kind", "RETRIEVER")
            retrieval.set_attribute("input.value", question)
            for index, document in enumerate(DOCUMENTS):
                prefix = f"retrieval.documents.{index}.document"
                retrieval.set_attribute(f"{prefix}.id", document["id"])
                retrieval.set_attribute(f"{prefix}.content", document["content"])
            context = "\n".join(document["content"] for document in DOCUMENTS)

        messages = [
            {
                "role": "system",
                "content": f"Answer only from these policies. Keep the two deadlines distinct.\n{context}",
            },
            {"role": "user", "content": question},
        ]
        with tracer.start_as_current_span("answer-with-model") as llm:
            llm.set_attribute("openinference.span.kind", "LLM")
            llm.set_attribute("llm.model_name", model)
            llm.set_attribute("input.value", json.dumps(messages))
            llm.set_attribute("input.mime_type", "application/json")
            response = client.chat.completions.create(model=model, messages=messages)
            result = response.choices[0].message.content or ""
            llm.set_attribute("output.value", result)
            if response.usage:
                llm.set_attribute("llm.token_count.prompt", response.usage.prompt_tokens)
                llm.set_attribute("llm.token_count.completion", response.usage.completion_tokens)
                llm.set_attribute("llm.token_count.total", response.usage.total_tokens)

        workflow.set_attribute("output.value", result)
        return result


def main() -> None:
    model = os.environ["OPENAI_MODEL"]
    provider = setup("phoenix-part-01-python")
    try:
        question = "My delivery arrived damaged. Which deadline applies?"
        print(answer(question, trace.get_tracer(__name__), OpenAI(), model))
    finally:
        provider.force_flush()
        provider.shutdown()


if __name__ == "__main__":
    main()
