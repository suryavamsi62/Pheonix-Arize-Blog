"""A bounded tool-calling agent using LangGraph and explicit instrumentation."""
import json
import os
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from openinference.instrumentation.langchain import LangChainInstrumentor

from telemetry import setup


# Expose this Python function as a tool the model can request.
@tool
def lookup_order_status(order_id: str) -> str:
    """Look up an order in the demonstration fixture."""
    # A fixed order record keeps this example independent of an external service.
    status = "shipped" if order_id == "88312" else "not found"
    return json.dumps({"order_id": order_id, "status": status})


# The graph carries a conversation history between nodes.
class State(TypedDict):
    # add_messages combines new messages with the existing history.
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph():
    # Describe the available tool to a model that supports tool calling.
    model = ChatOpenAI(model=os.environ["OPENAI_MODEL"], timeout=30, max_retries=1).bind_tools([lookup_order_status])

    # One node asks the model for its next response or tool request.
    def call_model(state):
        return {"messages": [model.invoke(state["messages"])]}

    # Continue to the tool node only when the latest response requests a tool.
    def route(state) -> Literal["tools", "done"]:
        return "tools" if getattr(state["messages"][-1], "tool_calls", None) else "done"

    # Define the two nodes and the routes between them.
    graph = StateGraph(State)
    graph.add_node("model", call_model)
    # ToolNode executes requested tools and adds their results to the conversation.
    graph.add_node("tools", ToolNode([lookup_order_status]))
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route, {"tools": "tools", "done": END})
    # Let the model read the tool result before deciding what to say next.
    graph.add_edge("tools", "model")
    return graph.compile()


if __name__ == "__main__":
    provider = setup("phoenix-part-01-langgraph")
    # Install the framework tracing hook once, before running the graph.
    LangChainInstrumentor().instrument(tracer_provider=provider)
    try:
        result = build_graph().invoke(
            {"messages": [SystemMessage(content="Use the lookup tool for order questions. Report its result without guessing."), HumanMessage(content="Where is order 88312?")]},
            # Bound graph execution so repeated tool requests cannot continue forever.
            config={"recursion_limit": 8},
        )
        print(result["messages"][-1].content)
    finally:
        # Export pending spans even if the graph raises an exception.
        provider.force_flush()
        provider.shutdown()
