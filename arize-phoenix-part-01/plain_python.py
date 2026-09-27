"""A fixed retrieval fixture and a real model call, manually traced."""
import json
import os

from openai import OpenAI

from telemetry import setup

# Fixed teaching data: no database search or similarity scoring is performed.
DOCUMENTS = [
    {"id": "returns", "content": "Standard returns are accepted within 30 days with a receipt."},
    {"id": "damage", "content": "Report damaged items within 48 hours of delivery."},
]


def answer(question, tracer, client, model):
    # One parent span groups the entire retrieve-and-answer workflow.
    with tracer.start_as_current_span("support-workflow") as root:
        root.set_attribute("openinference.span.kind", "CHAIN")
        # Attributes are named facts that we can inspect later in Phoenix.
        root.set_attribute("input.value", question)
        # Nesting this block makes retrieval a child of the workflow span.
        with tracer.start_as_current_span("retrieve-policy") as retrieval:
            retrieval.set_attribute("openinference.span.kind", "RETRIEVER")
            retrieval.set_attribute("input.value", question)
            # Record each document using the indexed OpenInference attribute names.
            for index, document in enumerate(DOCUMENTS):
                prefix = f"retrieval.documents.{index}.document"
                retrieval.set_attribute(f"{prefix}.id", document["id"])
                retrieval.set_attribute(f"{prefix}.content", document["content"])
            # Join the policy text into the context we will send to the model.
            context = "\n".join(document["content"] for document in DOCUMENTS)
        # The system message supplies the policies; the user message asks the question.
        messages = [
            {"role": "system", "content": f"Answer only from these policies. Keep the two deadlines distinct.\n{context}"},
            {"role": "user", "content": question},
        ]
        # Retrieval has ended. This model span is another child of the same parent.
        with tracer.start_as_current_span("answer-with-model") as llm:
            llm.set_attribute("openinference.span.kind", "LLM")
            llm.set_attribute("llm.model_name", model)
            # Store the messages as JSON text so the recorded input is inspectable.
            llm.set_attribute("input.value", json.dumps(messages))
            llm.set_attribute("input.mime_type", "application/json")
            # This is a real, billable model call. Tracing records what surrounds it.
            response = client.chat.completions.create(model=model, messages=messages)
            text = response.choices[0].message.content or ""
            llm.set_attribute("output.value", text)
            # Record token counts only when the model provider returns usage.
            if response.usage:
                llm.set_attribute("llm.token_count.prompt", response.usage.prompt_tokens)
                llm.set_attribute("llm.token_count.completion", response.usage.completion_tokens)
                llm.set_attribute("llm.token_count.total", response.usage.total_tokens)
        # Attach the final answer to the workflow as well as to the model call.
        root.set_attribute("output.value", text)
        return text


if __name__ == "__main__":
    # Read the selected model from the shell environment, not a hard-coded default.
    model = os.environ["OPENAI_MODEL"]
    provider = setup("phoenix-part-01-python")
    try:
        with OpenAI(timeout=30.0, max_retries=1) as client:
            print(answer("My order arrived damaged. Which deadline applies?", provider.get_tracer(__name__), client, model))
    finally:
        # Give buffered spans a chance to export, including when the run fails.
        provider.force_flush()
        provider.shutdown()
