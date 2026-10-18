"""Allowlisted failure states; never display SDK bodies, prompts or credentials."""
from datetime import datetime, timezone


MESSAGES = {
    "growth_units": "The AI returned inconsistent growth units (percentage versus decimal). Generate again; no automatic rescaling was applied.",
    "compatibility": "Complete the quote/statement compatibility review before generating an AI valuation.",
    "identity": "The AI response referred to a different company or evidence version. Generate again using the loaded company evidence.",
    "citations": "The AI response failed a source-reference check. Company metrics remain loaded; request status identifies the rejected field.",
    "eligibility": "The AI proposed targets or a directional opinion despite missing required evidence. Resolve the coverage issues before generating again.",
    "format": "The AI response did not match the required valuation format or driver bounds. Generate again to retry.",
    "length": "The AI response was cut off before the valuation was complete. Generate again to retry; no automatic retry was made.",
    "refusal": "The model declined this valuation request. No new valuation was saved.",
    "empty": "The model returned no completed valuation. Generate again to retry.",
    "budget": "The AI narrative exceeded the executive length limit. Generate again for a shorter valuation.",
}


class ValuationResponseError(ValueError):
    def __init__(self, code):
        self.code = code if code in MESSAGES else "format"
        super().__init__(MESSAGES[self.code])


def failure_state(error):
    """Only known categories/status/parameter names leave the exception boundary."""
    from openai import APIConnectionError, APITimeoutError, APIStatusError
    from pydantic import ValidationError
    if isinstance(error, ValuationResponseError):
        code, message = error.code, str(error)
    elif isinstance(error, (APITimeoutError, TimeoutError)):
        code, message = "timeout", "The AI request timed out. Your evidence is still loaded; generate again to retry."
    elif isinstance(error, APIConnectionError):
        code, message = "connection", "The app could not connect to OpenAI. Check connectivity and TLS configuration, then generate again."
    elif isinstance(error, APIStatusError):
        status = error.status_code
        if status == 401:
            code, message = "authentication", "OpenAI rejected the API credentials. Check the OpenAI key in Settings."
        elif status in (403, 404):
            code, message = "model_access", "The selected model is unavailable to this OpenAI project. Check model access or choose another configured model in Settings."
        elif status == 429:
            code, message = "rate_limit", "OpenAI reported a rate or quota limit. Check project usage and billing before retrying."
        elif status in (400, 422):
            code, message = "request", "OpenAI rejected the valuation request settings. Check the selected model; request status is shown below."
        else:
            code, message = "provider", "OpenAI could not complete the request. Your evidence is still loaded; try again later."
    elif isinstance(error, (ValidationError, ValueError)):
        code, message = "format", MESSAGES["format"]
    else:
        code, message = "unexpected", "The valuation could not complete because of an application error. No new valuation was accepted."
    result = dict(code=code, message=message, attempted_at=datetime.now(timezone.utc).isoformat())
    if isinstance(error, APIStatusError):
        result["http_status"] = error.status_code if isinstance(error.status_code, int) else None
        # SDK error text/body can contain user/provider content. Expose only known identifiers.
        parameter = getattr(error, "param", None)
        if parameter in {"model", "response_format", "response_format.json_schema", "reasoning_effort", "max_completion_tokens", "messages"}:
            result["parameter"] = parameter
        api_code = getattr(error, "code", None)
        if api_code in {"invalid_json_schema", "unsupported_parameter", "unsupported_value", "model_not_found", "insufficient_quota", "invalid_api_key"}:
            result["api_code"] = api_code
    if isinstance(error, ValuationResponseError) and hasattr(error,"diagnostics"):
        result["source_check"] = error.diagnostics
    return result
