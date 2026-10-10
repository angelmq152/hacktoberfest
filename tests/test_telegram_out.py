from output import telegram_out
from output.telegram_out import MAX_TEXT_LENGTH, _split, md_to_html, send
from shared.contracts import BotResponse, Confirmation


class FakeBot:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        async def method(**kw):
            self.calls.append((name, kw))
        return method


def test_table_becomes_aligned_pre_without_separator():
    out = md_to_html("Estado:\n| nombre | estado |\n|---|---|\n| redis | running |\n| worker-largo | exited |\nfin")
    assert out == ("Estado:\n<pre>nombre        estado\nredis         running\nworker-largo  exited</pre>\nfin")


def test_markup_inside_table_cells_is_stripped():
    assert md_to_html("| **Nombre** | `x` |\n| :--- | ---: |\n| a | b |") == "<pre>Nombre  x\na       b</pre>"


def test_heading_becomes_bold():
    assert md_to_html("### Logs de `x` & y") == "<b>Logs de `x` &amp; y</b>"


def test_inline_code_bold_and_escaping():
    assert md_to_html("**ojo** con `a<b>` & <script>") == "<b>ojo</b> con <code>a&lt;b&gt;</code> &amp; &lt;script&gt;"


def test_fenced_block_is_pre_and_escaped():
    assert md_to_html("logs:\n```\n<err> **x**\n```") == "logs:\n<pre>&lt;err&gt; **x**</pre>"


def test_unclosed_fence_still_closed():
    assert md_to_html("```\nline") == "<pre>line</pre>"


def test_split_respects_lines_and_limit():
    text = "\n".join(["a" * 3000, "b" * 3000, "c" * 10])
    chunks = _split(text)
    assert chunks == ["a" * 3000, "b" * 3000 + "\n" + "c" * 10]
    assert all(len(c) <= MAX_TEXT_LENGTH for c in _split("x" * 10000))
    assert "".join(_split("x" * 10000)) == "x" * 10000


async def test_send_without_tts_falls_back_to_text(monkeypatch):
    async def no_voice(text):
        return None
    monkeypatch.setattr(telegram_out, "get_voice_note", no_voice)
    bot = FakeBot()
    await send(bot, BotResponse(chat_id=1, speech="Hola <ya>", text="| a |\n|---|\n| 1 |",
                                confirmation=Confirmation(action_id="x1", prompt="¿Reinicio 'redis'?")))
    names = [c[0] for c in bot.calls]
    assert names == ["send_message", "send_message"]
    assert bot.calls[0][1]["text"] == "<i>(Audio no disponible)</i>\n\n<pre>a\n1</pre>"
    assert bot.calls[1][1]["reply_markup"].inline_keyboard[0][1].callback_data == "cancel:x1"


async def test_send_speech_only_escapes_fallback(monkeypatch):
    async def no_voice(text):
        return None
    monkeypatch.setattr(telegram_out, "get_voice_note", no_voice)
    bot = FakeBot()
    await send(bot, BotResponse(chat_id=1, speech="a < b"))
    assert bot.calls[0][1]["text"] == "<i>(Audio no disponible)</i>\n\na &lt; b"
