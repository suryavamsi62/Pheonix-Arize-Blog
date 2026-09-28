import os
from pathlib import Path

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# The local file wins if an older key is still set in the terminal.
load_dotenv(Path(__file__).with_name(".env"), override=True)


def setup(project_name: str):
    provider = TracerProvider(
        resource=Resource.create({"openinference.project.name": project_name})
    )
    exporter = OTLPSpanExporter(
        endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider
