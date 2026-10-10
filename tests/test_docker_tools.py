import pytest

from core.tools import TOOLS, docker_tools
from core.tools.base import ToolError
from core.tools.docker_tools import calc_cpu_percent, calc_memory, truncate_logs
from tests.conftest import make_stats


def test_registry_and_dangerous_flags():
    assert {"list_containers", "container_status", "container_logs", "container_stats", "restart_container",
            "stop_container", "start_container", "make_excel", "make_pdf", "make_chart",
            "docker_report"} == set(TOOLS)
    assert {n for n, t in TOOLS.items() if t.dangerous} == {"restart_container", "stop_container", "start_container"}


def test_list_names_only_managed():
    assert docker_tools.list_names() == ["db", "old", "web"]


@pytest.mark.parametrize("tool,args", [
    ("container_status", {"name": "secret"}),
    ("container_status", {"name": "nope"}),
    ("container_status", {"name": 5}),
    ("container_status", {}),
    ("container_status", {"name": "web", "extra": 1}),
    ("restart_container", {"name": "secret"}),
    ("container_logs", {"name": "web", "tail": 501}),
    ("container_logs", {"name": "web", "tail": 0}),
    ("container_logs", {"name": "web", "tail": "10"}),
    ("container_logs", {"name": "web", "tail": True}),
    ("container_logs", {"name": "web", "since": "yesterday"}),
    ("container_logs", {"name": "web", "since": 5}),
    ("container_logs", {"name": "web", "since": "99999999999d"}),
    ("list_containers", {"all": "yes"}),
    ("list_containers", {"foo": 1}),
    ("container_stats", {"name": "secret"}),
])
def test_validation_rejects(tool, args):
    with pytest.raises(ToolError):
        TOOLS[tool].validate(args)


def test_validation_accepts():
    assert TOOLS["container_logs"].validate({"name": "web"}) == {"name": "web", "tail": 100}
    assert TOOLS["container_logs"].validate({"name": "web", "tail": 500, "since": "10m"})["since"] == "10m"
    assert TOOLS["container_logs"].validate({"name": "web", "since": "2026-01-01T00:00:00Z"})
    assert TOOLS["container_stats"].validate({}) == {}
    assert TOOLS["container_stats"].validate({"name": ""}) == {}
    assert TOOLS["list_containers"].validate({}) == {"all": False}


def test_truncate_logs_keeps_tail():
    raw = b"A" * 5000 + b"END"
    out = truncate_logs(raw)
    assert out.startswith("[...truncated]")
    assert out.endswith("END")
    assert len(out.encode()) <= 4096 + 20
    assert truncate_logs(b"short") == "short"


def test_cpu_and_memory():
    assert calc_cpu_percent(make_stats(200, 1000, 2)) == 40.0
    assert calc_cpu_percent({}) == 0.0
    used, limit = calc_memory(make_stats())
    assert (used, limit) == (200.0, 1024.0)


async def test_list_status_logs_stats(ctx, containers):
    r = await TOOLS["list_containers"].run({"all": False}, ctx)
    assert "web" in r.data and "old" not in r.data and "secret" not in r.data
    r = await TOOLS["list_containers"].run({"all": True}, ctx)
    assert "old: exited" in r.data

    r = await TOOLS["container_status"].run({"name": "web"}, ctx)
    assert "running" in r.data and "health: healthy" in r.data and "restarts: 2" in r.data
    assert "uptime: 2h 5m" in r.data and "web:latest" in r.data
    r = await TOOLS["container_status"].run({"name": "old"}, ctx)
    assert "exit code: 137" in r.data and "uptime: -" in r.data

    containers[0]._logs = b"x" * 10000
    args = TOOLS["container_logs"].validate({"name": "web", "tail": 50, "since": "1h"})
    r = await TOOLS["container_logs"].run(args, ctx)
    assert len(r.data) < 4300 and "untrusted" in r.data
    kw = containers[0].calls[0][1]
    assert kw["tail"] == 50 and kw["since"] is not None

    r = await TOOLS["container_stats"].run({}, ctx)
    assert "web: running | cpu 40.0%" in r.data and "200/1024 MB" in r.data
    assert "old: exited | cpu 0.0%" in r.data


async def test_actions(ctx, containers):
    for tool, verb in [("restart_container", "restart"), ("stop_container", "stop"), ("start_container", "start")]:
        await TOOLS[tool].run(TOOLS[tool].validate({"name": "db"}), ctx)
        assert containers[1].calls[-1][0] == verb
