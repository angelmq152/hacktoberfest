from datetime import UTC, datetime, timedelta

import pytest

from core.tools import docker_tools
from core.tools.base import ToolContext
from shared.config import Settings, get_settings

LABEL = "hackbot.manage=true"


def make_stats(cpu_delta=200, sys_delta=1000, cpus=2, usage=300 * 1048576, cache=100 * 1048576, limit=1024 * 1048576):
    return {
        "cpu_stats": {"cpu_usage": {"total_usage": 1000 + cpu_delta}, "system_cpu_usage": 5000 + sys_delta,
                      "online_cpus": cpus},
        "precpu_stats": {"cpu_usage": {"total_usage": 1000}, "system_cpu_usage": 5000},
        "memory_stats": {"usage": usage, "stats": {"inactive_file": cache}, "limit": limit},
    }


class FakeContainer:
    def __init__(self, name, status="running", labels=None, logs=b"line1\n", restarts=0, health=None, exit_code=0):
        self.name = name
        self.status = status
        self.labels = labels if labels is not None else {"hackbot.manage": "true"}
        started = (datetime.now(UTC) - timedelta(hours=2, minutes=5, seconds=30)).strftime("%Y-%m-%dT%H:%M:%S.123456789Z")
        state = {"Running": status == "running", "StartedAt": started, "ExitCode": exit_code}
        if health:
            state["Health"] = {"Status": health}
        self.attrs = {"State": state, "RestartCount": restarts, "Config": {"Image": f"{name}:latest"}}
        self._logs = logs
        self.calls = []

    def logs(self, **kw):
        self.calls.append(("logs", kw))
        return self._logs

    def stats(self, stream=False):
        return make_stats()

    def restart(self):
        self.calls.append(("restart", {}))

    def stop(self):
        self.calls.append(("stop", {}))

    def start(self):
        self.calls.append(("start", {}))


class FakeContainers:
    def __init__(self, items):
        self.items = items

    def list(self, all=False, filters=None):
        label = (filters or {}).get("label")
        key, _, value = label.partition("=")
        return [c for c in self.items
                if c.labels.get(key) == value and (all or c.status == "running")]


class FakeClient:
    def __init__(self, items):
        self.containers = FakeContainers(items)


@pytest.fixture
def containers():
    return [
        FakeContainer("web", health="healthy", restarts=2),
        FakeContainer("db"),
        FakeContainer("old", status="exited", exit_code=137),
        FakeContainer("secret", labels={}),
    ]


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    # Tests must not depend on the developer's local .env (whitelist, tokens...)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for key in ("ALLOWED_USER_IDS", "OUT_DIR"):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def fake_docker(containers, monkeypatch):
    monkeypatch.setattr(docker_tools, "_client", FakeClient(containers))
    monkeypatch.setattr(docker_tools, "get_settings", lambda: type("S", (), {"managed_label": LABEL, "docker_host": ""})())


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(chat_id=1, user_id=1, out_dir=tmp_path / "out" / "1")
