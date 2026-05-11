from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from langgraphagenticai.nodes.chatbot_with_Tool_node import create_tool_enabled_finance_node
from langgraphagenticai.state.state import State


class GraphBuilder:
    def __init__(self, llm, tools, system_prompt: str):
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt

    def build_finance_graph(self):
        graph_builder = StateGraph(State)

        chatbot_node = create_tool_enabled_finance_node(
            llm=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )
        tool_node = ToolNode(self.tools)

        graph_builder.add_node("chatbot", chatbot_node)
        graph_builder.add_node("tools", tool_node)

        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")

        # tools_condition already routes chatbot -> END when no tool call is needed.
        # Do NOT add an unconditional chatbot -> END edge, or LangGraph can stop
        # before the ToolNode has a chance to execute data-fetching tool calls.
        return graph_builder.compile(checkpointer=MemorySaver())
