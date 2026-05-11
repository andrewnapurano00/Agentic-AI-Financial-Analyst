from __future__ import annotations

import re
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage


TABLE_HINT_PATTERNS = [
    r"\btable\b",
    r"\btabular\b",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bscorecard\b",
    r"\bmatrix\b",
    r"\brank(?:ed|ing)?\b",
    r"\bsummary table\b",
]


def _is_table_request(text: str) -> bool:
    txt = (text or "").lower()
    return any(re.search(pattern, txt) for pattern in TABLE_HINT_PATTERNS)


def _latest_user_text(messages: List[object]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                return content.strip()
            return str(content).strip()
    return ""


def _table_mode_instruction() -> str:
    return """
The user requested a table or comparison-style output.

Return valid JSON only.
Do not include markdown fences.
Do not include explanatory prose before or after the JSON.

Use this exact schema:
{
  "response_type": "table",
  "title": "Short title",
  "columns": ["Column 1", "Column 2", "Column 3"],
  "rows": [
    ["row1col1", "row1col2", "row1col3"],
    ["row2col1", "row2col2", "row2col3"]
  ],
  "takeaways": [
    "Short takeaway 1",
    "Short takeaway 2"
  ]
}

Rules:
- Prefer a single clean table unless the user explicitly asks for multiple tables.
- Keep columns concise.
- Use "N/A" for missing values.
- Make rows rectangular so every row has the same number of columns.
- If comparing companies, include the ticker as the first column.
- Put any brief conclusions in "takeaways", not outside the JSON.
"""


def _prose_mode_instruction() -> str:
    return """
Write in a polished equity-research style.

Formatting rules:
- Start with a short executive summary of 1-2 sentences when the request is analytical.
- Prefer short sections over long bullet dumps.
- Use at most 5 bullets unless the user explicitly asks for more detail.
- Keep each bullet focused on one idea.
- Normalize financial figures clearly, for example: $68.0B, $194.0B, 75.0%.
- Avoid decorative symbols, cluttered punctuation, and repeated labels.
- End with a short bottom-line conclusion when appropriate.
- If the answer is simple, answer directly without over-formatting.
"""


def create_tool_enabled_finance_node(llm, tools, system_prompt: str):
    llm_with_tools = llm.bind_tools(tools)

    def finance_node(state):
        messages = state["messages"]
        latest_user_text = _latest_user_text(messages)

        full_messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content=_prose_mode_instruction()),
        ]

        if _is_table_request(latest_user_text):
            full_messages.append(SystemMessage(content=_table_mode_instruction()))

        full_messages.extend(messages)
        response = llm_with_tools.invoke(full_messages)
        return {"messages": [response]}

    return finance_node