from app.services.ai.provider import _strip_code_fence


def test_strips_json_code_fence() -> None:
    assert _strip_code_fence('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_strips_bare_code_fence() -> None:
    assert _strip_code_fence('```\n{"b": 2}\n```') == '{"b": 2}'


def test_passes_through_plain_json() -> None:
    assert _strip_code_fence('{"c": 3}') == '{"c": 3}'
