from __future__ import annotations

from typing import Dict, List


def validate_runtime_config(
    openai_api_key: str,
    fmp_api_key: str,
    marketaux_api_key: str,
    selected_model: str,
) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not openai_api_key:
        errors.append("OPENAI_API_KEY is required.")

    if not selected_model:
        errors.append("An OpenAI model must be selected.")

    if not fmp_api_key:
        warnings.append("FMP_API_KEY is not set. Fundamentals, price, and transcript tools will be unavailable.")

    if not marketaux_api_key:
        warnings.append("MARKETAUX_API_KEY is not set. Enhanced news tools will be unavailable.")

    return {
        "errors": errors,
        "warnings": warnings,
    }