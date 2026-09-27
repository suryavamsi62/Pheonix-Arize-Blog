import os

from phoenix.otel import register


def setup(project_name):
    # Create the provider that exports spans to Phoenix; this does not start Phoenix.
    return register(
        # Group this example under its own project in the Phoenix UI.
        project_name=project_name,
        # Use a configured collector, or send to the server on this computer.
        endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
        # Send traces over HTTP using OTLP, the OpenTelemetry export protocol.
        protocol="http/protobuf",
        # Each example installs its own hooks, so avoid automatic duplicate setup.
        auto_instrument=False,
        # Send spans in groups; short scripts must flush before exiting.
        batch=True,
    )
