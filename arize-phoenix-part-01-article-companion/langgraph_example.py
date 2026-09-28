"""A small tool-calling graph with a fixed sample order."""

import os
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from openai import OpenAI
from openinference.instrumentation.langchain import LangChainInstrumentor

from telemetry import setup


class State(TypedDict):
    messages: Annotated[list, add_messages]


def lookup_order_status(order_id: str) -> str:
    if order_id == "88312":
        return "Order 88312 is out for delivery and is expected tomorrow."
    return f"No sample order found for {order_id}."


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order_status",
            "description": "Look up the status of a sample order by its ID.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    }
]


def main() -> None:
    # LangGraph owns the node loop; the OpenAI call and sample tool are explicit.
    import json

    provider = setup("phoenix-part-01-langgraph")
    LangChainInstrumentor().instrument(tracer_provider=provider)
    client = OpenAI()
    model_name = os.environ["OPENAI_MODEL"]

    def model_node(state: State) -> State:
        api_messages = [{"role": "system", "content": "Use the order tool before answering an order-status question."}]
        for message in state["messages"]:
            if isinstance(message, HumanMessage):
                api_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, ToolMessage):
                api_messages.append({"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content})
            elif isinstance(message, AIMessage):
                item = {"role": "assistant", "content": message.content or None}
                if message.tool_calls:
                    item["tool_calls"] = [
                        {"id": call["id"], "type": "function", "function": {"name": call["name"], "arguments": json.dumps(call["args"])}}
                        for call in message.tool_calls
                    ]
                api_messages.append(item)
        response = client.chat.completions.create(model=model_name, messages=api_messages, tools=TOOLS)
        output = response.choices[0].message
        calls = [
            {"id": call.id, "name": call.function.name, "args": json.loads(call.function.arguments)}
            for call in (output.tool_calls or [])
        ]
        return {"messages": [AIMessage(content=output.content or "", tool_calls=calls)]}

    def tool_node(state: State) -> State:
        result = []
        for call in state["messages"][-1].tool_calls:
            if call["name"] != "lookup_order_status":
                raise ValueError(f"Unknown tool: {call['name']}")
            result.append(ToolMessage(content=lookup_order_status(call["args"]["order_id"]), tool_call_id=call["id"]))
        return {"messages": result}

    def route(state: State) -> str:
        return "tool" if state["messages"][-1].tool_calls else END

    graph = StateGraph(State)
    graph.add_node("model", model_node)
    graph.add_node("tool", tool_node)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route)
    graph.add_edge("tool", "model")
    app = graph.compile()
    try:
        result = app.invoke({"messages": [HumanMessage(content="Where is order 88312?")]}, config={"recursion_limit": 8})
        print(result["messages"][-1].content)
    finally:
        provider.force_flush()
        provider.shutdown()


if __name__ == "__main__":
    main()
