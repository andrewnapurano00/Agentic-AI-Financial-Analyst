from langgraphagenticai.utils.app_health import validate_runtime_config


def test_validate_runtime_config_missing_openai():
    result = validate_runtime_config(
        openai_api_key="",
        fmp_api_key="abc",
        marketaux_api_key="xyz",
        selected_model="gpt-5",
    )

    assert len(result["errors"]) == 1
    assert "OPENAI_API_KEY" in result["errors"][0]


def test_validate_runtime_config_warnings():
    result = validate_runtime_config(
        openai_api_key="abc",
        fmp_api_key="",
        marketaux_api_key="",
        selected_model="gpt-5",
    )

    assert result["errors"] == []
    assert len(result["warnings"]) == 2