import pytest

from core.llm import Final, LLMParseError, ToolCall, _to_gemini_contents, parse_model_output


def test_plain_tool_call():
    assert parse_model_output('{"tool": "list_containers", "args": {"all": true}}') == ToolCall(
        "list_containers", {"all": True}
    )


def test_tool_without_args():
    assert parse_model_output('{"tool": "x"}') == ToolCall("x", {})


def test_final():
    assert parse_model_output('{"final": {"speech": "hola", "text": "t"}}') == Final("hola", "t")


def test_final_without_text():
    assert parse_model_output('{"final": {"speech": "hola"}}') == Final("hola", "")


def test_json_fence_and_surrounding_text():
    raw = 'Claro:\n```json\n{"tool": "a", "args": {"n": {"x": 1}}}\n```\nListo.'
    assert parse_model_output(raw) == ToolCall("a", {"n": {"x": 1}})


def test_braces_inside_strings():
    raw = '{"final": {"speech": "usa } y { con cuidado", "text": "```{x}```"}}'
    assert parse_model_output(raw) == Final("usa } y { con cuidado", "```{x}```")


def test_garbage_braces_before_json():
    raw = 'nota {no es json} y luego {"tool": "a", "args": {}}'
    assert parse_model_output(raw) == ToolCall("a", {})


def test_first_object_wins():
    raw = '{"tool": "a", "args": {}} {"tool": "b", "args": {}}'
    assert parse_model_output(raw).tool == "a"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "sin json",
        '{"tool": "a", "args": ',
        "[1, 2]",
        '{"foo": 1}',
        '{"tool": "a", "args": [1]}',
        '{"tool": ""}',
        '{"final": "texto"}',
        '{"final": {"text": "sin speech"}}',
    ],
)
def test_invalid(raw):
    with pytest.raises(LLMParseError):
        parse_model_output(raw)


def test_gemini_contents_system_as_user_and_merged():
    msgs = [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "U"},
        {"role": "assistant", "content": "A"},
    ]
    assert _to_gemini_contents(msgs) == [
        {"role": "user", "parts": [{"text": "S\n\nU"}]},
        {"role": "model", "parts": [{"text": "A"}]},
    ]
