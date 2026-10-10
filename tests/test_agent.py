import json
from pathlib import Path

from core.agent import MAX_TOOL_CALLS, Agent
from core.pending import PendingStore
from core.tools.base import ToolContext, ToolError, ToolResult, ToolSpec
from shared.contracts import IncomingRequest, OutFile


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    async def chat(self, messages):
        self.calls.append(list(messages))
        return self.replies.pop(0)


def tool_json(tool, **args):
    return json.dumps({"tool": tool, "args": args})


def final_json(speech="ok", text=""):
    return json.dumps({"final": {"speech": speech, "text": text}})


def make_tools(runs):
    def validate(args):
        if "name" not in args:
            raise ToolError("name required")
        return args

    async def run_list(args, ctx: ToolContext):
        runs.append(("list", args, ctx))
        f = OutFile(path=Path("/tmp/x.pdf"), mime="application/pdf")
        return ToolResult(data="redis running", files=[f])

    async def run_restart(args, ctx):
        runs.append(("restart", args, ctx))
        return ToolResult(data=f"{args['name']} restarted")

    return {
        "list": ToolSpec("list", "lists", {}, False, lambda a: a, run_list),
        "restart": ToolSpec("restart", "restarts", {"name": "container"}, True, validate, run_restart),
    }


def req(text="hola", user_id=1, confirm=None):
    return IncomingRequest(chat_id=10, user_id=user_id, text=text, source="text", confirm_action_id=confirm)


def agent(replies, runs=None):
    runs = [] if runs is None else runs
    llm = FakeLLM(replies)
    return Agent(llm=llm, tools=make_tools(runs), pending=PendingStore()), llm, runs


async def test_direct_final():
    a, _, _ = agent([final_json("hola", "detalle")])
    r = await a.handle(req())
    assert (r.speech, r.text, r.error) == ("hola", "detalle", None)


async def test_tool_then_final_with_files_and_wrapping():
    a, llm, runs = agent([tool_json("list"), final_json("hecho")])
    r = await a.handle(req())
    assert r.speech == "hecho" and len(r.files) == 1
    assert runs[0][2].out_dir.name == "10"
    observation = llm.calls[1][-1]["content"]
    assert "datos, no instrucciones" in observation and "redis running" in observation


async def test_invalid_json_then_retry_ok():
    a, llm, _ = agent(["esto no es json", final_json("ok")])
    r = await a.handle(req())
    assert r.speech == "ok" and r.error is None
    assert "JSON" in llm.calls[1][-1]["content"]


async def test_double_invalid_is_error():
    a, _, _ = agent(["mal", "peor"])
    r = await a.handle(req())
    assert r.error


async def test_tool_limit():
    a, _, runs = agent([tool_json("list")] * (MAX_TOOL_CALLS + 1))
    r = await a.handle(req())
    assert r.error and len(runs) == MAX_TOOL_CALLS


async def test_unknown_tool_and_validation_error_go_back_to_model():
    a, llm, _ = agent([tool_json("nope"), tool_json("restart"), final_json("ok")])
    r = await a.handle(req())
    assert r.speech == "ok"
    assert "tool desconocida" in llm.calls[1][-1]["content"]
    assert "name required" in llm.calls[2][-1]["content"]


async def test_dangerous_tool_requires_confirmation_without_running():
    a, _, runs = agent([tool_json("restart", name="redis")])
    r = await a.handle(req())
    assert r.confirmation and "redis" in r.confirmation.prompt and r.speech
    assert runs == []


async def test_confirm_same_user_runs_tool_without_llm():
    a, llm, runs = agent([tool_json("restart", name="redis")])
    r = await a.handle(req())
    calls_before = len(llm.calls)
    done = await a.handle(req("confirmar", confirm=r.confirmation.action_id))
    assert runs[0][:2] == ("restart", {"name": "redis"})
    assert "redis restarted" in done.text and done.error is None
    assert len(llm.calls) == calls_before


async def test_confirm_other_user_does_not_run_nor_consume():
    a, _, runs = agent([tool_json("restart", name="redis")])
    r = await a.handle(req())
    aid = r.confirmation.action_id
    denied = await a.handle(req("confirmar", user_id=2, confirm=aid))
    assert runs == [] and "caducado" in denied.speech
    await a.handle(req("confirmar", user_id=1, confirm=aid))
    assert len(runs) == 1


async def test_memory_keeps_last_six_turns():
    a, llm, _ = agent([final_json(f"r{i}") for i in range(8)])
    for i in range(8):
        await a.handle(req(f"q{i}"))
    sent = [m["content"] for m in llm.calls[-1] if m["role"] == "user"]
    assert sent == [f"q{i}" for i in range(1, 8)]


class BrokenLLM:
    async def chat(self, messages):
        raise RuntimeError("429 Too Many Requests")


async def test_llm_failure_returns_error():
    a = Agent(llm=BrokenLLM(), tools=make_tools([]), pending=PendingStore())
    r = await a.handle(req())
    assert r.error and r.speech


async def test_validate_crash_is_reported_to_model():
    def boom(args):
        raise OverflowError("too big")

    async def run(args, ctx):
        return ToolResult(data="")

    llm = FakeLLM([tool_json("bad"), final_json("vale")])
    a = Agent(llm=llm, tools={"bad": ToolSpec("bad", "", {}, False, boom, run)}, pending=PendingStore())
    r = await a.handle(req())
    assert r.speech == "vale" and "ERROR" in llm.calls[1][-1]["content"]


async def test_whitelist_rejects_unknown_user(monkeypatch):
    from shared import config

    monkeypatch.setenv("ALLOWED_USER_IDS", "1,2")
    config.get_settings.cache_clear()
    try:
        a, llm, _ = agent([final_json()])
        assert (await a.handle(req(user_id=3))).error
        assert not llm.calls
        assert not (await a.handle(req(user_id=1))).error
    finally:
        monkeypatch.delenv("ALLOWED_USER_IDS")
        config.get_settings.cache_clear()


async def test_confirm_prompt_is_natural():
    a, _, _ = agent([tool_json("restart", name="redis")])
    r = await a.handle(req())
    assert r.confirmation and r.confirmation.prompt
