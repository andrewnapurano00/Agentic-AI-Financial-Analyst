from __future__ import annotations

from langchain_openai import ChatOpenAI


class OpenAILLM:
    def __init__(self, user_controls_input: dict):
        self.user_controls_input = user_controls_input

    def get_llm_model(self):
        api_key = (self.user_controls_input.get("OPENAI_API_KEY") or "").strip()
        model = (self.user_controls_input.get("selected_model") or "gpt-5").strip()

        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")

        kwargs = {
            "api_key": api_key,
            "model": model,
            "timeout": 60,
            "max_retries": 2,
        }

        # Some GPT-5 variants reject temperature explicitly.
        if not model.lower().startswith("gpt-5"):
            kwargs["temperature"] = 0.1

        return ChatOpenAI(**kwargs)