from types import SimpleNamespace

import pytest

from input import telegram_in
from shared.config import get_settings


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_chat_action(self, **kw):
        pass

    async def send_message(self, **kw):
        self.sent.append(kw["text"])


class FakeFile:
    async def download_to_memory(self, out, **kw):
        out.write(b"ogg")


class FakeVoice:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    async def get_file(self, **kw):
        self.calls += 1
        if self.calls <= self.failures:
            raise TimeoutError("Timed out")
        return FakeFile()


@pytest.fixture
def allowed(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "42")
    get_settings.cache_clear()


def voice_update(voice):
    message = SimpleNamespace(voice=voice, audio=None, text=None)
    return SimpleNamespace(effective_user=SimpleNamespace(id=42, username="u"), effective_chat=SimpleNamespace(id=7),
                           callback_query=None, message=message)


def stt_returning(text):
    async def fake(audio):
        return text
    return fake


async def test_download_is_retried_once(allowed, monkeypatch):
    monkeypatch.setattr(telegram_in, "transcribe_audio", stt_returning("lista los contenedores"))
    voice, bot = FakeVoice(failures=1), FakeBot()
    req = await telegram_in.to_request(voice_update(voice), SimpleNamespace(bot=bot))
    assert req.text == "lista los contenedores" and req.source == "voice"
    assert voice.calls == 2 and bot.sent == []


async def test_download_failure_tells_user_and_skips_core(allowed, monkeypatch):
    monkeypatch.setattr(telegram_in, "transcribe_audio", stt_returning("no debería llegar"))
    bot = FakeBot()
    req = await telegram_in.to_request(voice_update(FakeVoice(failures=2)), SimpleNamespace(bot=bot))
    assert req is None and bot.sent == [telegram_in.AUDIO_DOWNLOAD_ERROR]


async def test_empty_transcription_tells_user_and_skips_core(allowed, monkeypatch):
    monkeypatch.setattr(telegram_in, "transcribe_audio", stt_returning("  "))
    bot = FakeBot()
    req = await telegram_in.to_request(voice_update(FakeVoice(failures=0)), SimpleNamespace(bot=bot))
    assert req is None and bot.sent == [telegram_in.AUDIO_STT_ERROR]
