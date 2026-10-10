from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass
class IncomingRequest:
    chat_id: int
    user_id: int
    text: str                                # transcription or typed text
    source: Literal["voice", "text", "callback"]
    lang: str = "es"
    confirm_action_id: str | None = None     # set when the user presses "Confirm"

@dataclass
class OutFile:
    path: Path
    mime: str                                # application/pdf, xlsx, image/png...
    caption: str = ""

@dataclass
class Confirmation:
    action_id: str                           # pending action stored in core
    prompt: str                              # "¿Reinicio 'redis'?"

@dataclass
class BotResponse:
    chat_id: int
    speech: str                              # SHORT text for TTS, no markdown
    text: str = ""                           # markdown detail (tables, logs)
    files: list[OutFile] = field(default_factory=list)
    confirmation: Confirmation | None = None
    error: str | None = None
